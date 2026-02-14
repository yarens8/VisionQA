
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import asyncio

from database import get_db
from database.models import TestCase, TestStep, TestRun, TestStatus
from executors.web.web_executor import WebExecutor

router = APIRouter(prefix="/execution", tags=["execution"])

@router.post("/run-case/{case_id}")
async def run_test_case_live(case_id: int, db: Session = Depends(get_db)):
    """
    CANLI TEST KOŞUSU 🎬
    Bir Test Case'i adım adım çalıştırır ve sonuçları döner.
    """
    # 1. Test Case'i Bul
    test_case = db.query(TestCase).filter(TestCase.id == case_id).first()
    
    steps_to_run = []
    if test_case:
        # DB'den sıralı adımları al
        steps_to_run = sorted(test_case.steps, key=lambda s: s.order)
    
    # 2. Eğer DB'de adım yoksa (veya Test Case boşsa), DEMO MODU çalıştır
    if not steps_to_run or len(steps_to_run) == 0:
        print("⚠️ DB'de adım bulunamadı (veya boş), VisionQA Demo (Google) Testi çalıştırılıyor...")
        # Demo Adımları
        steps_to_run = [
            TestStep(order=1, action="navigate", target="https://www.google.com", expected_result="Açıldı"),
            TestStep(order=2, action="type", target="textarea[name='q']", value="VisionQA AI Testing", expected_result="Yazıldı"),
            TestStep(order=3, action="wait", target="2000", expected_result=" beklendi"), # 2 sn bekle
            TestStep(order=4, action="verify", target="textarea[name='q']", expected_result="Göründü")
        ]

    # 3. TestRun Kaydı Oluştur (Veritabanına Kayıt Başlıyor 💾)
    test_run = TestRun(
        project_id=test_case.project_id if test_case else 1, # Demo ise default 1
        test_case_id=case_id,
        platform="web", # Şimdilik hardcoded
        module_name="live_execution",
        target=steps_to_run[0].target if steps_to_run else "unknown",
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    # KULLANICI İSTEĞİ: "Benim gözümün önünde test etsin"
    executor = WebExecutor(headless=False)
    
    execution_report = {
        "case_id": case_id,
        "run_id": test_run.id,
        "status": "running",
        "steps": []
    }

    try:
        await executor.start()
        
        # --- ADIM ADIM KOŞMA ---
        for step in steps_to_run:
            step_result = {
                "order": step.order,
                "action": step.action,
                "target": step.target,
                "status": "pending",
                "error": None
            }
            
            try:
                print(f"▶️ Adım {step.order}: {step.action} -> {step.target}")
                
                if step.action == "navigate":
                    await executor.navigate(step.target)
                
                elif step.action == "click":
                    await executor.click_element(step.target)
                
                elif step.action == "type":
                    await executor.type_input(step.target, step.value or "")
                
                elif step.action == "verify":
                    exists = await executor.verify_element(step.target)
                    if not exists:
                        raise Exception(f"Element bulunamadı: {step.target}")

                elif step.action == "wait":
                    # target '2000' string gelebilir
                    wait_ms = int(step.target) if step.target.isdigit() else 1000
                    await asyncio.sleep(wait_ms / 1000)

                # Başarılı
                step_result["status"] = "passed"
                
            except Exception as e:
                # 🛑 SOFT ASSERTION: Hata olsa bile devam et (Kullanıcı İsteği)
                print(f"❌ Adım {step.order} Başarısız: {str(e)}")
                step_result["status"] = "failed"
                step_result["error"] = str(e)
                # Hata bulgusu oluştur (Finding)
                # (İleride buraya Finding tablosuna kayıt ekleyeceğiz)

            execution_report["steps"].append(step_result)
            
            # Her adım arasında çok kısa bekle
            await asyncio.sleep(0.5)

        # Genel Durum Belirleme
        has_failure = any(s["status"] == "failed" for s in execution_report["steps"])
        final_status = "failed" if has_failure else "completed"
        
        execution_report["status"] = final_status

    except Exception as e:
        print(f"⛔ Test Motoru Hatası: {str(e)}")
        execution_report["status"] = "crashed"
        execution_report["error"] = str(e)
    
    finally:
        await executor.stop()
        
        # 4. TestRun Kaydını Güncelle (Bitiş) 💾
        test_run.status = execution_report["status"]
        test_run.completed_at = datetime.utcnow()
        import json
        test_run.logs = json.dumps(execution_report["steps"]) # Adım sonuçlarını JSON olarak sakla
        db.commit()
    
    return execution_report

@router.get("/runs", response_model=List[Dict[str, Any]])
def get_test_runs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    Geçmiş test koşularını listele
    """
    runs = db.query(TestRun).order_by(TestRun.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for run in runs:
        result.append({
            "id": run.id,
            "project_id": run.project_id,
            "platform": run.platform,
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "target": run.target
        })
    return result
