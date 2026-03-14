
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import asyncio
import concurrent.futures
import json
import os
import time

from database import get_db, SessionLocal
from database.models import TestCase, TestStep, TestRun, TestStatus, Project
from executors.web.web_executor import WebExecutor

router = APIRouter(prefix="/execution", tags=["execution"])
LIVE_RUNS: Dict[int, Dict[str, Any]] = {}


class StartCaseRequest(BaseModel):
    live_mode: bool = False


def _default_policy(action: str) -> Dict[str, Any]:
    if action == "navigate":
        return {"required": True, "timeout_ms": 60000, "retry": 1, "fallback_allowed": False}
    if action in ["click", "type", "verify"]:
        return {"required": True, "timeout_ms": 8000, "retry": 2, "fallback_allowed": True}
    if action == "wait":
        return {"required": True, "timeout_ms": 20000, "retry": 0, "fallback_allowed": False}
    return {"required": True, "timeout_ms": 8000, "retry": 1, "fallback_allowed": True}


def _semantic_locators(action: str, target: str) -> List[str]:
    t = (target or "").lower()
    selectors: List[str] = []

    if action == "type":
        if any(k in t for k in ["email", "e-posta", "mail"]):
            selectors.extend([
                "input[type='email']",
                "input[name*='email' i]",
                "input[id*='email' i]",
                "input[autocomplete='email']",
                "input[autocomplete='username']",
                "input[name*='user' i]",
                "input[placeholder*='mail' i]",
                "input[placeholder*='e-posta' i]",
                "input[inputmode='email']",
                "input:not([type='hidden']):not([disabled])",
            ])
        elif any(k in t for k in ["password", "şifre", "sifre"]):
            selectors.extend([
                "input[type='password']",
                "input[name*='password' i]",
                "input[id*='password' i]",
                "input[autocomplete='current-password']",
                "input[placeholder*='şifre' i]",
                "input[placeholder*='sifre' i]",
                "input:not([type='hidden']):not([disabled])",
            ])
        else:
            selectors.extend([
                "form input:not([type='hidden']):not([disabled])",
                "input[type='text']:not([disabled])",
                "input:not([type='hidden']):not([disabled])",
                "textarea",
            ])

    if action == "click":
        if any(k in t for k in ["submit", "continue", "devam", "login", "giriş", "giris"]):
            selectors.extend([
                "button[type='submit']",
                "button:has-text('Devam Et')",
                "button:has-text('Giriş Yap')",
                "button:has-text('Login')",
                "button:has-text('Continue')",
            ])
        if any(k in t for k in ["cookie", "consent", "accept", "reject", "cerez", "kvkk"]):
            selectors.extend([
                "button:has-text('Accept')",
                "button:has-text('Kabul')",
                "button:has-text('Reddet')",
                "button:has-text('Reject')",
                "[id*='cookie' i] button",
            ])

    if action == "verify":
        if any(k in t for k in ["error", "alert", "hata", "uyarı", "uyari"]):
            selectors.extend([
                ".error, .error-message, .alert, [role='alert']",
                "text=geçersiz",
                "text=hatalı",
                "text=zorunlu",
                "text=invalid",
            ])

    return selectors


def _compile_step_dsl(raw_step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy step formatını Step DSL v1'e çevirir.
    Legacy örnek: {"order":1,"action":"click","target":"button:has-text('Submit')","value":""}
    DSL v1: intent + locator_chain + policy + expected
    """
    action = str(raw_step.get("action", "interact")).strip().lower()
    target = str(raw_step.get("target", "")).strip()
    value = raw_step.get("value", "")
    order = int(raw_step.get("order", 1))

    locator_chain = []
    if raw_step.get("locator_chain") and isinstance(raw_step.get("locator_chain"), list):
        locator_chain = [str(x).strip() for x in raw_step["locator_chain"] if str(x).strip()]
    # Önce semantic zincir, sonra modelin verdiği/legacy target.
    for sel in _semantic_locators(action, target):
        if sel not in locator_chain:
            locator_chain.append(sel)
    if target and target not in locator_chain:
        locator_chain.append(target)

    policy = _default_policy(action)
    if isinstance(raw_step.get("policy"), dict):
        policy.update(raw_step["policy"])

    # Yaygın opsiyonel banner tıklamalarını zorunlu olmayan adım olarak işaretle
    target_lower = target.lower()
    if action == "click" and any(k in target_lower for k in ["cookie", "consent", "accept", "reject", "cerez", "kvkk"]):
        policy["required"] = False

    expected = raw_step.get("expected")
    expected_dsl = {"type": "none", "matchers": []}
    if isinstance(expected, dict):
        expected_dsl["type"] = str(expected.get("type", "none"))
        matchers = expected.get("matchers", [])
        if isinstance(matchers, list):
            expected_dsl["matchers"] = [str(m).strip() for m in matchers if str(m).strip()]
    elif action == "verify":
        expected_dsl = {
            "type": "verify_visible",
            "matchers": [target] if target else []
        }

    intent = str(raw_step.get("intent", f"{action}_{target[:40] if target else 'step'}"))
    return {
        "order": order,
        "intent": intent,
        "action": action,
        "target_hint": target,
        "locator_chain": locator_chain,
        "value": value,
        "policy": policy,
        "expected": expected_dsl,
    }


def _compile_steps_dsl(steps_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_compile_step_dsl(s) for s in steps_data]


def _serialize_steps_for_log(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "order":        s.get("order"),
            "intent":       s.get("intent", ""),
            "action":       s.get("action"),
            "action_label": s.get("action_label", ""),
            "target":       s.get("target", ""),
            "selector_used": s.get("selector_used", ""),
            "attempts":     s.get("attempts", []),
            "value":        s.get("value", ""),
            "status":       s.get("status"),
            "reason":       s.get("reason", ""),
            "error":        s.get("error"),
            "healing":      s.get("healing"),
            "duration_ms":  s.get("duration_ms", 0),
        }
        for s in steps
    ]


async def _background_run_case(
    run_id: int,
    case_id: int,
    steps_data: List[Dict[str, Any]],
    test_title: str,
    run_options: Dict[str, Any]
):
    """Case'i arkaplanda çalıştır, canlı durumları belleğe yaz, sonunda DB'ye kaydet."""
    LIVE_RUNS[run_id] = {
        "run_id": run_id,
        "case_id": case_id,
        "status": "running",
        "steps": [],
        "summary": "Çalıştırma başlatıldı...",
    }

    # Live mode açıksa gerçek Playwright penceresi zaten görünür olur.
    # Bu durumda ekstra bridge şovu açmıyoruz.
    if not bool(run_options.get("live_mode", False)):
        # ── CANLI ŞOV SİNYALİ: Bridge'e test bilgilerini gönder ──
        try:
            import requests
            bridge_payload = {
                "url": steps_data[0]["target"] if steps_data and steps_data[0]["action"] == "navigate" else "unknown",
                "test_title": test_title,
                "steps": steps_data
            }
            bridge_candidates = [
                os.getenv("DESKTOP_BRIDGE_URL", "").strip().rstrip("/"),
                "http://127.0.0.1:8001",
                "http://localhost:8001",
                "http://host.docker.internal:8001",
            ]
            for base in [b for b in bridge_candidates if b]:
                try:
                    requests.post(f"{base}/deploy-test", json=bridge_payload, timeout=(2, 5))
                    print(f"🎬 [Bridge] Canlı test şovu başlatıldı: {test_title} ({base})")
                    break
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️ [Bridge] Canlı şov sinyali gönderilemedi (test yine de çalışacak): {e}")
        # ─────────────────────────────────────────────────────────

    def on_step_update(current_steps: List[Dict[str, Any]], status: str, summary: str = ""):
        LIVE_RUNS[run_id] = {
            "run_id": run_id,
            "case_id": case_id,
            "status": status,
            "steps": current_steps,
            "summary": summary or LIVE_RUNS.get(run_id, {}).get("summary", ""),
        }

    # Tipik negatif senaryolarda LLM bazen type value boş dönebiliyor.
    # Koşu öncesi minimum güvenli değerlerle tamamlıyoruz.
    normalized_steps = []
    for s in steps_data:
        s2 = dict(s)
        if s2.get("action") == "type" and not str(s2.get("value", "")).strip():
            target_lower = str(s2.get("target", "")).lower()
            if "email" in target_lower or "e-posta" in target_lower:
                s2["value"] = "invalid-email-format"
            elif "password" in target_lower or "şifre" in target_lower:
                s2["value"] = "123"
            else:
                s2["value"] = "invalid-input"
        normalized_steps.append(s2)
    dsl_steps = _compile_steps_dsl(normalized_steps)

    try:
        execution_report = await _execute_steps(
            dsl_steps,
            on_step_update=on_step_update,
            run_options=run_options
        )
        execution_report["case_id"] = case_id
        execution_report["run_id"] = run_id
    except Exception as run_err:
        execution_report = {
            "case_id": case_id,
            "run_id": run_id,
            "status": "crashed",
            "steps": LIVE_RUNS.get(run_id, {}).get("steps", []),
            "summary": f"Koşu beklenmeyen şekilde durdu: {run_err}",
            "error": str(run_err),
        }

    # DB status enum: pending|running|completed|failed (crashed → failed)
    db_status = execution_report["status"]
    if db_status == "crashed":
        db_status = "failed"

    db = SessionLocal()
    try:
        test_run = db.query(TestRun).filter(TestRun.id == run_id).first()
        if test_run:
            test_run.status = db_status
            test_run.completed_at = datetime.utcnow()
            test_run.logs = json.dumps(
                {
                    "summary": execution_report.get("summary", "Özet yok."),
                    "steps": _serialize_steps_for_log(execution_report.get("steps", [])),
                },
                ensure_ascii=False
            )
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ TestRun güncelleme hatası (async): {e}")
    finally:
        db.close()

    LIVE_RUNS[run_id] = {
        "run_id": run_id,
        "case_id": case_id,
        "status": execution_report.get("status", "failed"),
        "steps": execution_report.get("steps", []),
        "summary": execution_report.get("summary", "Özet yok."),
    }


@router.post("/start-case/{case_id}")
async def start_test_case_live(
    case_id: int,
    request: StartCaseRequest,
    db: Session = Depends(get_db)
):
    """
    Asenkron test koşusu başlatır ve hemen run_id döner.
    Frontend bu run_id ile /execution/run-status/{run_id} endpoint'ini poll eder.
    """
    if case_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Bu test case henüz veritabanına kaydedilmedi. Lütfen önce case'i kaydedin."
        )

    test_case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not test_case:
        raise HTTPException(status_code=404, detail=f"Test case bulunamadı (ID: {case_id})")

    steps_to_run = sorted(test_case.steps, key=lambda s: s.order)
    if not steps_to_run:
        raise HTTPException(status_code=400, detail="Bu test case'in hiç adımı yok.")

    steps_data = [
        {
            "order": s.order,
            "action": s.action,
            "target": s.target or "",
            "value": s.value or "",
        }
        for s in steps_to_run
    ]

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

    asyncio.create_task(
        _background_run_case(
            run_id=test_run.id,
            case_id=case_id,
            steps_data=steps_data,
            test_title=test_case.title,
            run_options={"live_mode": request.live_mode}
        )
    )

    return {
        "run_id": test_run.id,
        "case_id": case_id,
        "status": "running",
        "live_mode": request.live_mode
    }


@router.get("/run-status/{run_id}")
def get_run_status(run_id: int, db: Session = Depends(get_db)):
    """
    Canlı run durumunu döner. Önce bellekten, yoksa DB logundan cevap verir.
    """
    if run_id in LIVE_RUNS:
        return LIVE_RUNS[run_id]

    test_run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not test_run:
        raise HTTPException(status_code=404, detail=f"Run bulunamadı: {run_id}")

    parsed_logs = {}
    if test_run.logs:
        try:
            parsed_logs = json.loads(test_run.logs)
        except Exception:
            parsed_logs = {}

    return {
        "run_id": run_id,
        "case_id": test_run.test_case_id,
        "status": str(test_run.status.value if hasattr(test_run.status, "value") else test_run.status),
        "summary": parsed_logs.get("summary", ""),
        "steps": parsed_logs.get("steps", []),
    }

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

    # ── CANLI ŞOV SİNYALİ: Bridge'e test bilgilerini gönder ──
    try:
        import urllib.request
        bridge_payload = json.dumps({
            "url": steps_data[0]["target"] if steps_data and steps_data[0]["action"] == "navigate" else "unknown",
            "test_title": test_case.title,
            "steps": steps_data
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://host.docker.internal:8001/deploy-test",
            data=bridge_payload, method="POST",
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=3)
        print(f"🎬 [Bridge] Canlı test şovu başlatıldı: {test_case.title}")
    except Exception as e:
        print(f"⚠️ [Bridge] Canlı şov sinyali gönderilemedi (test yine de çalışacak): {e}")
    # ─────────────────────────────────────────────────────────

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
                    "duration_ms":  s.get("duration_ms", 0),
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


async def _execute_steps(
    steps_data: List[Dict],
    on_step_update=None,
    run_options: Dict[str, Any] = None
) -> Dict:
    """Playwright adımlarını çalıştırır, kendi event loop'unda."""
    from executors.web.web_executor import WebExecutor
    from core.agents.self_healing_executor import SelfHealingExecutor
    import asyncio
    import base64
    import tempfile
    import os

    run_options = run_options or {}
    live_mode = bool(run_options.get("live_mode", False))

    # Live mode: gerçek tarayıcı açık, highlight açık.
    # Fast mode: headless + highlight kapalı.
    web_executor = WebExecutor(
        headless=not live_mode,
        highlight_enabled=live_mode
    )
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
            action = str(step.get("action", "interact"))
            action_label = ACTION_LABELS.get(action, action)
            locator_chain = step.get("locator_chain", []) or []
            policy = step.get("policy", {}) or {}
            required = bool(policy.get("required", True))
            retry_count = int(policy.get("retry", 1))

            step_result = {
                "order":        step["order"],
                "intent":       step.get("intent", ""),
                "action":       action,
                "action_label": action_label,
                "target":       step.get("target_hint", step.get("target", "")),
                "selector_used": "",
                "attempts":     [],
                "value":        step.get("value", ""),
                "status":       "pending",
                "reason":       "",
                "error":        None,
                "screenshot":   "",
                "healing":      None, # AI iyileştirme raporu buraya gelecek
                "duration_ms":  0
            }
            step_start = time.perf_counter()
            try:
                print(f"▶️ Adım {step['order']}: {action} -> {step.get('target_hint', '')}")

                async def _run_with_locators(fn_name: str, value: str = ""):
                    target_text = str(step.get("target_hint", step.get("target", ""))).lower()
                    selectors = [s for s in locator_chain if s]
                    # DSL/legacy uyumluluğu: target_hint yoksa legacy "target" alanını da kullan.
                    if not selectors:
                        hint = str(step.get("target_hint", "")).strip()
                        legacy_target = str(step.get("target", "")).strip()
                        if hint:
                            selectors.append(hint)
                        if legacy_target and legacy_target not in selectors:
                            selectors.append(legacy_target)

                    # Son güvenlik ağı: type/verify için genel selector fallback'leri.
                    if not selectors and fn_name == "type":
                        if any(k in target_text for k in ["email", "e-posta", "mail"]):
                            selectors.extend([
                                "input[type='email']",
                                "input[name*='email' i]",
                                "input[id*='email' i]",
                                "input[autocomplete='email']",
                                "input[autocomplete='username']",
                                "input[placeholder*='mail' i]",
                                "input[placeholder*='e-posta' i]",
                                "input:not([type='hidden']):not([disabled])",
                            ])
                        elif any(k in target_text for k in ["password", "şifre", "sifre"]):
                            selectors.extend([
                                "input[type='password']",
                                "input[name*='password' i]",
                                "input[id*='password' i]",
                                "input[autocomplete='current-password']",
                                "input[placeholder*='şifre' i]",
                                "input[placeholder*='sifre' i]",
                                "input:not([type='hidden']):not([disabled])",
                            ])
                        else:
                            selectors.extend([
                                "form input:not([type='hidden']):not([disabled])",
                                "input[type='text']:not([disabled])",
                                "input:not([type='hidden']):not([disabled])",
                                "textarea:not([disabled])",
                            ])
                    if not selectors and fn_name == "click":
                        if any(k in target_text for k in ["submit", "continue", "devam", "login", "giriş", "giris", "sign in"]):
                            selectors.extend([
                                "button[type='submit']",
                                "input[type='submit']",
                                "button:has-text('Devam Et')",
                                "button:has-text('Giriş Yap')",
                                "button:has-text('Login')",
                                "button:has-text('Sign In')",
                            ])
                        elif any(k in target_text for k in ["cookie", "consent", "accept", "reject", "cerez", "kvkk"]):
                            selectors.extend([
                                "button:has-text('Accept')",
                                "button:has-text('Kabul')",
                                "button:has-text('Reddet')",
                                "button:has-text('Reject')",
                            ])
                        else:
                            selectors.extend([
                                "button:visible",
                                "[role='button']:visible",
                                "a:visible",
                            ])
                    if not selectors and fn_name == "verify":
                        selectors.extend([
                            ".error, .error-message, .alert, [role='alert']",
                            "text=geçersiz",
                            "text=invalid",
                        ])

                    async def _attempt_with(selectors_to_try: List[str]):
                        last_error = None
                        for _ in range(max(1, retry_count)):
                            for sel in selectors_to_try:
                                try:
                                    if fn_name == "click":
                                        await executor.click(sel)
                                    elif fn_name == "type":
                                        await executor.type(sel, value)
                                    elif fn_name == "verify":
                                        if await executor.verify(sel):
                                            step_result["selector_used"] = sel
                                            return True, None
                                        raise Exception(f"verify false: {sel}")
                                    step_result["selector_used"] = sel
                                    return True, None
                                except Exception as e:
                                    last_error = e
                                    step_result["attempts"].append({"selector": sel, "error": str(e)})
                        return False, last_error

                    success, last_err = await _attempt_with(selectors)
                    if success:
                        return True

                    # İlk tur başarısızsa olası overlay/cookie engelini temizleyip bir tur daha dene.
                    if fn_name in ["click", "type"]:
                        await executor.handle_global_obstacles()
                        success, last_err = await _attempt_with(selectors)
                        if success:
                            return True

                    if fn_name == "verify":
                        return False
                    raise last_err if last_err else Exception("no selectors available")

                if action == "navigate":
                    await executor.navigate(step.get("target_hint", step.get("target", "")))
                    step_result["reason"] = f"{step.get('target_hint', '')} adresine gidildi ve sayfa temizlendi."

                elif action == "click":
                    clicked = False
                    try:
                        clicked = await _run_with_locators("click")
                    except Exception as click_err:
                        target_lower = str(step.get("target_hint", "")).lower()
                        optional_keywords = ["cookie", "consent", "accept", "reject", "kvkk", "cerez", "tanimlama", "allow"]
                        if any(k in target_lower for k in optional_keywords):
                            await executor.handle_global_obstacles()
                            clicked = not required
                            step_result["reason"] = f"Opsiyonel banner adımı atlandı/temizlendi: `{step.get('target_hint','')}` ({click_err})"
                        else:
                            submit_like = ["submit", "continue", "devam", "login", "giriş"]
                            if any(k in target_lower for k in submit_like):
                                step["locator_chain"] = list(dict.fromkeys(locator_chain + [
                                    "button:has-text('Devam Et')",
                                    "button:has-text('Giriş Yap')",
                                    "button[type='submit']",
                                ]))
                                locator_chain = step["locator_chain"]
                                clicked = await _run_with_locators("click")
                            else:
                                raise
                    if not clicked and required:
                        raise Exception(f"`{step.get('target_hint','')}` click başarısız.")
                    if not step_result["reason"]:
                        step_result["reason"] = f"`{step_result['selector_used'] or step.get('target_hint','')}` elementine tıklandı."

                elif action == "type":
                    await _run_with_locators("type", value=str(step.get("value", "")))
                    step_result["reason"] = f"`{step_result['selector_used'] or step.get('target_hint','')}` alanına yazıldı."

                elif action == "verify":
                    success = await _run_with_locators("verify")
                    if not success:
                        target_lower = str(step.get("target_hint", "")).lower()
                        if "error" in target_lower or "alert" in target_lower:
                            step["locator_chain"] = list(dict.fromkeys(locator_chain + [
                                ".error, .error-message, .alert, [role='alert']",
                                "text=geçersiz",
                                "text=hatalı",
                                "text=zorunlu",
                            ]))
                            locator_chain = step["locator_chain"]
                            success = await _run_with_locators("verify")
                    if not success and required:
                        raise Exception(f"`{step.get('target_hint','')}` doğrulaması başarısız.")
                    if not step_result["reason"]:
                        step_result["reason"] = f"`{step_result['selector_used'] or step.get('target_hint','')}` doğrulandı."

                elif action == "wait":
                    target = str(step.get("target_hint", step.get("target", ""))).strip().lower()
                    if target in ["networkidle", "domcontentloaded", "load"]:
                        await web_executor.page.wait_for_load_state(target, timeout=20000)
                        step_result["reason"] = f"Load state beklendi: {target}"
                    elif target.startswith("selector:"):
                        selector = target.split("selector:", 1)[1].strip()
                        await web_executor.page.locator(selector).first.wait_for(timeout=15000)
                        step_result["reason"] = f"Selector göründü: {selector}"
                        step_result["selector_used"] = selector
                    elif target.endswith("ms") and target[:-2].isdigit():
                        wait_ms = int(target[:-2])
                        await asyncio.sleep(wait_ms / 1000)
                        step_result["reason"] = f"{wait_ms}ms beklendi."
                    elif target.endswith("s") and target[:-1].isdigit():
                        wait_s = int(target[:-1])
                        await asyncio.sleep(wait_s)
                        step_result["reason"] = f"{wait_s}s beklendi."
                    else:
                        wait_ms = int(target) if target.isdigit() else 1000
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

            step_result["duration_ms"] = int((time.perf_counter() - step_start) * 1000)
            # Her adım sonrası screenshot al (Şimdilik devre dışı)
            # step_result["screenshot"] = await take_screenshot_base64()
            report["steps"].append(step_result)
            if on_step_update:
                on_step_update(report["steps"], "running")
            if step_result["status"] == "failed" and required:
                report["abort_reason"] = (
                    f"Adım {step.get('order')} ({action}) başarısız oldu; "
                    "zorunlu adım hatasında koşu durduruldu."
                )
                break

        has_failure = any(s["status"] == "failed" for s in report["steps"])
        report["status"] = "failed" if has_failure else "completed"

        # LLM özeti uzun sürebilir; varsayılan hızlı modda kapalı.
        summary_enabled = os.getenv("EXECUTION_SUMMARY_ENABLED", "false").lower() == "true"
        if summary_enabled:
            try:
                from core.models.llm_client import LLMClient
                llm = LLMClient()
                summary_logs = ""
                for s in report["steps"]:
                    summary_logs += (
                        f"Step {s['order']}: {s['action']} -> {s['status']} "
                        f"({s.get('duration_ms', 0)}ms). {s.get('reason','')}\n"
                    )
                report["summary"] = await llm.generate_execution_summary(summary_logs)
                print(f"📄 [AI Summary]: {report['summary']}")
            except Exception as e:
                print(f"⚠️ Özet oluşturulamadı: {e}")
                report["summary"] = "Test özeti oluşturulamadı."
        else:
            passed = sum(1 for s in report["steps"] if s.get("status") == "passed")
            total = len(report["steps"])
            total_ms = sum(int(s.get("duration_ms", 0)) for s in report["steps"])
            abort_suffix = ""
            if report.get("abort_reason"):
                abort_suffix = f" Koşu durduruldu: {report['abort_reason']}"
            report["summary"] = f"{passed}/{total} adım tamamlandı. Toplam süre: {total_ms}ms.{abort_suffix}"
        if on_step_update:
            on_step_update(report["steps"], report["status"], report.get("summary", ""))

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
