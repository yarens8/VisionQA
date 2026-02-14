
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

    # KULLANICI İSTEĞİ: "Benim gözümün önünde test etsin"
    executor = WebExecutor(headless=False)
    
    execution_report = {
        "case_id": case_id,
        "status": "completed",
        "steps": []
    }

    try:
        await executor.start()
        
        # --- ADIM ADIM KOŞMA ---
        for step in steps_to_run:
            step_result = {
                "order": step.order,
                "action": step.action,
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
                # continue döngüyü bozmaz, sonraki adıma geçer

            execution_report["steps"].append(step_result)
            
            # Her adım arasında çok kısa bekle ki kullanıcı görsün (Human-like)
            await asyncio.sleep(1.0)

    except Exception as e:
        print(f"⛔ Test Motoru Hatası: {str(e)}")
        execution_report["status"] = "crashed"
        execution_report["error"] = str(e)
    
    finally:
        await executor.stop()
    
    return execution_report
