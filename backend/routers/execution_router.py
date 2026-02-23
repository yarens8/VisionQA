
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import asyncio
import concurrent.futures
import json

from database import get_db
from database.models import TestCase, TestStep, TestRun, TestStatus, Project
from executors.web.web_executor import WebExecutor

router = APIRouter(prefix="/execution", tags=["execution"])

@router.post("/run-case/{case_id}")
async def run_test_case_live(case_id: int, db: Session = Depends(get_db)):
    """
    CANLI TEST KOŞUSU 🎬
    Bir Test Case'i adım adım çalıştırır ve sonuçları döner.
    """
    # 1. Test Case'i DB'de bul
    if case_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Bu test case henüz veritabanına kaydedilmedi. Lütfen önce 'Generate with AI' sırasında 'Save to Project' seçeneğini aktif edin."
        )

    test_case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not test_case:
        raise HTTPException(status_code=404, detail=f"Test case bulunamadı (ID: {case_id})")

    steps_to_run = sorted(test_case.steps, key=lambda s: s.order)
    if not steps_to_run:
        raise HTTPException(status_code=400, detail="Bu test case'in hiç adımı yok. Lütfen önce AI ile yeniden üretin.")

    # Steps'i serileştir (thread'e geçmek için)
    steps_data = [
        {
            "order": s.order,
            "action": s.action,
            "target": s.target or "",
            "value": s.value or "",
        }
        for s in steps_to_run
    ]

    # 2. TestRun Kaydı Oluştur
    try:
        test_run = TestRun(
            project_id=test_case.project_id,
            test_case_id=test_case.id,
            platform="web",
            module_name="live_execution",
            target=steps_data[0]["target"] if steps_data else "unknown",
            status="running",
            started_at=datetime.utcnow()
        )
        db.add(test_run)
        db.commit()
        db.refresh(test_run)
        run_id = test_run.id
    except Exception as e:
        print(f"⚠️ TestRun kaydı oluşturulamadı: {e}")
        run_id = None

    # 3. Playwright'ı ayrı thread'de çalıştır (Windows event loop fix)
    def run_playwright_sync(steps):
        """Kendi event loop'uyla ayrı thread'de çalışır."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_execute_steps(steps))
        finally:
            loop.close()

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        execution_report = await loop.run_in_executor(pool, run_playwright_sync, steps_data)

    execution_report["case_id"] = case_id
    execution_report["run_id"] = run_id

    # 4. TestRun Kaydını Güncelle
    if run_id:
        try:
            # DB status enum: pending|running|completed|failed (crashed → failed)
            db_status = execution_report["status"]
            if db_status == "crashed":
                db_status = "failed"

            # Screenshot'ları çıkar (dev base64 veriler DB'ye yazılmaz)
            steps_for_log = [
                {
                    "order":        s.get("order"),
                    "action":       s.get("action"),
                    "action_label": s.get("action_label", ""),
                    "target":       s.get("target", ""),
                    "value":        s.get("value", ""),
                    "status":       s.get("status"),
                    "reason":       s.get("reason", ""),
                    "error":        s.get("error"),
                    "healing":      s.get("healing"), # AI Onarım detaylarını ekleyelim
                }
                for s in execution_report.get("steps", [])
            ]

            test_run.status = db_status
            test_run.completed_at = datetime.utcnow()
            
            # Tüm rapor verisini tek bir JSON'da toplayalım
            final_report = {
                "summary": execution_report.get("summary", "Özet yok."),
                "steps": steps_for_log
            }
            test_run.logs = json.dumps(final_report, ensure_ascii=False)
            db.commit()
            print(f"✅ TestRun #{run_id} kaydedildi: {db_status}")
        except Exception as e:
            print(f"⚠️ TestRun güncelleme hatası: {e}")
            import traceback; traceback.print_exc()

    return execution_report


async def _execute_steps(steps_data: List[Dict]) -> Dict:
    """Playwright adımlarını çalıştırır, kendi event loop'unda."""
    from executors.web.web_executor import WebExecutor
    from core.agents.self_healing_executor import SelfHealingExecutor
    import asyncio
    import base64
    import tempfile
    import os

    web_executor = WebExecutor(headless=False)
    executor = SelfHealingExecutor(web_executor)
    
    report = {"status": "running", "steps": []}

    async def take_screenshot_base64() -> str:
        """Anlık ekran görüntüsünü base64 olarak döner."""
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp_path = tmp.name
            tmp.close()
            await web_executor.screenshot(tmp_path)
            with open(tmp_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            os.unlink(tmp_path)
            return f"data:image/png;base64,{data}"
        except Exception:
            return ""

    ACTION_LABELS = {
        "navigate": "Sayfaya git",
        "click":    "Elemente tıkla",
        "type":     "Metin gir",
        "verify":   "Elementi doğrula",
        "wait":     "Bekle",
    }

    try:
        await web_executor.start()

        for step in steps_data:
            action_label = ACTION_LABELS.get(step["action"], step["action"])
            step_result = {
                "order":        step["order"],
                "action":       step["action"],
                "action_label": action_label,
                "target":       step["target"],
                "value":        step.get("value", ""),
                "status":       "pending",
                "reason":       "",
                "error":        None,
                "screenshot":   "",
                "healing":      None # AI iyileştirme raporu buraya gelecek
            }
            try:
                print(f"▶️ Adım {step['order']}: {step['action']} -> {step['target']}")

                if step["action"] == "navigate":
                    await executor.navigate(step["target"])
                    step_result["reason"] = f"{step['target']} adresine gidildi ve sayfa temizlendi."

                elif step["action"] == "click":
                    await executor.click(step["target"])
                    step_result["reason"] = f"`{step['target']}` elementine tıklandı."

                elif step["action"] == "type":
                    await executor.type(step["target"], step["value"])
                    step_result["reason"] = f"`{step['target']}` alanına yazıldı."

                elif step["action"] == "verify":
                    success = await executor.verify(step["target"])
                    if not success:
                        raise Exception(f"`{step['target']}` doğrulaması başarısız.")
                    step_result["reason"] = f"`{step['target']}` doğrulandı."

                elif step["action"] == "wait":
                    wait_ms = int(step["target"]) if str(step["target"]).isdigit() else 1000
                    await asyncio.sleep(wait_ms / 1000)
                    step_result["reason"] = f"{wait_ms}ms beklendi."

                # İyileştirme yapıldı mı kontrol et
                if executor.last_healing_report:
                    step_result["healing"] = executor.last_healing_report
                    step_result["reason"] += " (AI tarafından otomatik olarak onarıldı! ✨)"
                    executor.last_healing_report = None # Bir sonraki adım için sıfırla

                step_result["status"] = "passed"

            except Exception as e:
                print(f"❌ Adım {step['order']} Başarısız: {str(e)}")
                step_result["status"] = "failed"
                step_result["error"] = str(e)
                step_result["reason"] = str(e)
                # Fail durumunda da healing raporu varsa ekle (neden iyileştirilemediği bilgisi için)
                if executor.last_healing_report:
                    step_result["healing"] = executor.last_healing_report
                    executor.last_healing_report = None

            # Her adım sonrası screenshot al (Şimdilik devre dışı)
            # step_result["screenshot"] = await take_screenshot_base64()
            report["steps"].append(step_result)
            await asyncio.sleep(0.3)

        has_failure = any(s["status"] == "failed" for s in report["steps"])
        report["status"] = "failed" if has_failure else "completed"

        # AI Özet Analizi Oluştur
        try:
            from core.models.llm_client import LLMClient
            llm = LLMClient()
            # Özet için logları formatla
            summary_logs = ""
            for s in report["steps"]:
                summary_logs += f"Step {s['order']}: {s['action']} -> {s['status']}. {s.get('reason','')}\n"
            
            report["summary"] = await llm.generate_execution_summary(summary_logs)
            print(f"📄 [AI Summary]: {report['summary']}")
        except Exception as e:
            print(f"⚠️ Özet oluşturulamadı: {e}")
            report["summary"] = "Test özeti oluşturulamadı."

    except Exception as e:
        print(f"⛔ Test Motoru Hatası: {str(e)}")
        import traceback; traceback.print_exc()
        report["status"] = "crashed"
        report["error"] = str(e)
        report["summary"] = f"Test motoru çöktü: {str(e)}"
    finally:
        await web_executor.stop()

    return report



@router.get("/runs", response_model=List[Dict[str, Any]])
def get_test_runs(
    project_id: int = None,
    platform: str = None,
    status: str = None,
    skip: int = 0, 
    limit: int = 50, 
    db: Session = Depends(get_db)
):
    """
    Geçmiş test koşularını listele ve filtrele
    """
    query = db.query(TestRun, Project.name.label("project_name")).join(Project, TestRun.project_id == Project.id)

    if project_id:
        query = query.filter(TestRun.project_id == project_id)
    if platform:
        query = query.filter(TestRun.platform == platform)
    if status:
        query = query.filter(TestRun.status == status)

    runs = query.order_by(TestRun.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for run, project_name in runs:
        result.append({
            "id":           run.id,
            "project_id":   run.project_id,
            "project_name": project_name, # Yeni alan
            "platform":     run.platform.value if hasattr(run.platform, 'value') else str(run.platform),
            "status":       run.status.value if hasattr(run.status, 'value') else str(run.status),
            "started_at":   run.started_at,
            "completed_at": run.completed_at,
            "target":       run.target,
            "logs":         run.logs,
        })
    return result
