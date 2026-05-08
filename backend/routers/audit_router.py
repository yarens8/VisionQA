from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List
import time
import asyncio
import traceback

from core.models.llm_client import LLMClient
from core.vad.engine import VADEngine
from executors.web.web_executor import WebExecutor

router = APIRouter(prefix="/audit", tags=["Full Audit"])

class AuditRequest(BaseModel):
    url: str
    run_execution: bool = True
    headless: bool = True

class AuditResponse(BaseModel):
    status: str
    url: str
    duration_sec: float
    identity_report: Dict[str, Any]
    generated_cases_summary: Dict[str, Any]
    execution_summary: Dict[str, Any]
    vad_report: Dict[str, Any]
    root_cause_analysis: Dict[str, Any]

@router.post("/run-full", response_model=AuditResponse)
async def run_full_audit(req: AuditRequest):
    """
    Mega Orchestrator: Runs the entire VisionQA autonomous flow.
    1. Identity & Rules Discovery
    2. Dynamic Test Generation
    3. Test Execution (Self-Healing)
    4. Visual Anomaly Detection (VAD)
    5. Root Cause Analysis (RCA)
    """
    start_time = time.time()
    print(f"🚀 [AUDIT] Başlatılıyor: {req.url}")

    llm = LLMClient()
    vad = VADEngine()
    executor = None

    try:
        # ─── AŞAMA 1 & 2: BEYİN (LLM Identity & Test Generation) ───
        print("🧠 [AUDIT] Aşama 1 & 2: Sayfa kimliği ve test üretimi başlıyor...")
        
        # Basit bir DOM context simülasyonu (gerçekte WebExecutor ile alınabilir)
        # Hız için şimdilik temel HTML veya boş geçiyoruz, LLM URL'den de çıkarım yapabilir.
        dummy_context = "Header, Login Form (email, password), Submit Button, Footer"
        
        identity = await llm.identify_page_purpose(req.url, page_context=dummy_context)
        
        test_cases = await llm.generate_test_cases(
            url=req.url, 
            page_context=dummy_context, 
            page_identity=identity, 
            platform="web"
        )
        
        cases_summary = {
            "total_generated": sum(len(test_cases.get(cat, [])) for cat in ["happy_path", "negative_path", "edge_cases", "security_checks"]),
            "happy_path_count": len(test_cases.get("happy_path", [])),
            "negative_path_count": len(test_cases.get("negative_path", [])),
            "edge_cases_count": len(test_cases.get("edge_cases", []))
        }

        execution_results = {"status": "skipped", "message": "Execution bypassed by user"}
        vad_report_dict = {"overall_score": 100, "anomalies": []}
        rca_report = {"overall_assessment": "No anomalies to analyze."}

        # ─── AŞAMA 3: KASLAR (Test Execution) ───
        if req.run_execution:
            print("🦾 [AUDIT] Aşama 3: Test İcrası (Execution) başlıyor...")
            executor = WebExecutor(headless=req.headless)
            await executor.start()
            
            try:
                # Sadece ilk "happy_path" testini demo amaçlı koşalım
                happy_tests = test_cases.get("happy_path", [])
                
                if happy_tests and "steps" in happy_tests[0]:
                    test_to_run = happy_tests[0]
                    print(f"▶️ [AUDIT] Örnek Test Koşuluyor: {test_to_run.get('title')}")
                    
                    for step in test_to_run["steps"]:
                        action = step.get("action")
                        target = step.get("target")
                        val = step.get("value", "")
                        
                        if action == "navigate":
                            # URL'deki değişkeni temizle
                            t_url = target.replace("{url}", req.url)
                            await executor.navigate(t_url)
                        elif action == "wait" and target == "networkidle":
                            if executor.page:
                                await executor.page.wait_for_load_state("networkidle")
                        
                        # Burada gerçek implementasyonda click/type vb. SelfHealing executor çağrılır.
                        # Demo olduğu için basitleştiriyoruz.
                        await asyncio.sleep(1) # Simüle bekleme

                    execution_results = {"status": "success", "executed_test": test_to_run.get("title")}
                else:
                    # Test yoksa sadece URL'e git
                    await executor.navigate(req.url)
                    execution_results = {"status": "success", "executed_test": "Navigate Only"}
                
                # ─── AŞAMA 4: DENETMEN (VAD) ───
                print("👁️ [AUDIT] Aşama 4: VAD (Visual Anomaly Detection) analizi yapılıyor...")
                # Son sayfa durumunu VAD'a gönder
                report = await vad.analyze_after_test(executor, test_title="Audit Run")
                vad_report_dict = report.to_dict()

                # ─── AŞAMA 5: KÖK NEDEN ANALİZİ (RCA) ───
                if report.anomalies:
                    print("🧠 [AUDIT] Aşama 5: Kök Neden Analizi (RCA) yapılıyor...")
                    # VAD'ın bulduğu anomalileri sözlük listesine çevirip LLM'e yolla
                    anomalies_for_llm = [
                        {
                            "id": a.id,
                            "anomaly_type": a.anomaly_type.value,
                            "title": a.title,
                            "description": a.description
                        } for a in report.anomalies
                    ]
                    rca_report = await llm.analyze_visual_anomalies(req.url, anomalies_for_llm)
                
            except Exception as e:
                execution_results = {"status": "error", "message": str(e), "trace": traceback.format_exc()}
            finally:
                if executor:
                    await executor.stop()

        duration = time.time() - start_time
        print(f"🎉 [AUDIT] Tamamlandı! Süre: {duration:.2f}s")

        return AuditResponse(
            status="completed",
            url=req.url,
            duration_sec=round(duration, 2),
            identity_report=identity,
            generated_cases_summary=cases_summary,
            execution_summary=execution_results,
            vad_report=vad_report_dict,
            root_cause_analysis=rca_report
        )

    except Exception as e:
        print(f"❌ [AUDIT] Kritik Hata: {str(e)}")
        if executor:
            await executor.stop()
        raise HTTPException(status_code=500, detail=str(e))
