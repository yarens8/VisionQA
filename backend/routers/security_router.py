import base64
import io
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from sqlalchemy.orm import Session

import schemas
from core.security.engine import SecurityEngine
from database import get_db
from database.models import SecurityAnalysisRecord
from executors.web.web_executor import WebExecutor


router = APIRouter(prefix="/security", tags=["security"])
engine = SecurityEngine()


def _inject_query(url: str, key: str, value: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _record_meta(record: SecurityAnalysisRecord) -> dict:
    payload = dict(record.analysis_payload or {})
    meta = dict(payload.get("_history_meta") or {})
    payload["_history_meta"] = meta
    return payload


def _build_thumbnail_base64(source_image_base64: str, max_size: tuple[int, int] = (240, 160)) -> str | None:
    if not source_image_base64:
        return None
    try:
        image_bytes = base64.b64decode(source_image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image.thumbnail(max_size)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


def _save_security_record(db: Session, result: dict, *, source_type: str, source_label: str | None = None, source_url: str | None = None) -> None:
    try:
        record = SecurityAnalysisRecord(
            platform=result.get("platform", "web"),
            source_type=source_type,
            source_label=source_label,
            source_url=source_url,
            overall_score=int(result.get("overall_score") or 0),
            findings_count=len(result.get("findings") or []),
            overview=result.get("overview") or "",
            analysis_payload=result,
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Security history save failed: {exc}")


def _history_item_schema(record: SecurityAnalysisRecord) -> schemas.SecurityHistoryItem:
    payload = record.analysis_payload or {}
    meta = (payload.get("_history_meta") or {})
    source_image_base64 = ((payload.get("artifacts") or {}).get("source_image_base64")) or None
    return schemas.SecurityHistoryItem(
        id=record.id,
        platform=record.platform,
        source_type=record.source_type,
        source_label=record.source_label,
        source_url=record.source_url,
        is_favorite=bool(meta.get("is_favorite", False)),
        overall_score=record.overall_score,
        findings_count=record.findings_count,
        overview=record.overview or "",
        thumbnail_base64=_build_thumbnail_base64(source_image_base64),
        created_at=record.created_at,
    )


@router.post("/analyze-image", response_model=schemas.SecurityAnalysisResponse)
async def analyze_security_image(request: schemas.SecurityAnalysisRequest, db: Session = Depends(get_db)):
    try:
        result = engine.analyze_image(
            image_base64=request.image_base64,
            platform=request.platform,
        )
        _save_security_record(db, result, source_type="upload", source_label="Manuel security screenshot analizi")
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Security image analysis failed: {exc}") from exc


@router.post("/analyze-url", response_model=schemas.SecurityAnalysisResponse)
async def analyze_security_url(request: schemas.SecurityUrlAnalysisRequest, db: Session = Depends(get_db)):
    if request.platform != "web":
        raise HTTPException(status_code=400, detail="URL-based security analysis is currently supported only for web.")

    executor = WebExecutor(headless=request.headless)
    response_headers: dict[str, str] = {}
    response_text = ""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
            response = await client.get(request.url)
            response_headers = dict(response.headers)
            content_type = response.headers.get("content-type", "")
            response_text = response.text[:5000] if "text" in content_type or "json" in content_type or "html" in content_type else ""
    except Exception:
        response_headers = {}
        response_text = ""

    try:
        await executor.start()
        await executor.navigate(request.url)
        screenshot_bytes = await executor.screenshot(full_page=request.full_page)
        image_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        result = engine.analyze_image(
            image_base64=image_base64,
            platform="web",
            response_text=response_text,
            response_headers=response_headers,
            url=request.url,
        )
        _save_security_record(db, result, source_type="url", source_label="Canli security URL analizi", source_url=request.url)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Security URL analysis failed: {exc}") from exc
    finally:
        try:
            await executor.stop()
        except Exception:
            pass


@router.post("/simulate-url", response_model=schemas.SecuritySimulationResponse)
async def simulate_security_url(request: schemas.SecuritySimulationRequest):
    if request.platform != "web":
        raise HTTPException(status_code=400, detail="Active simulation starter is currently supported only for web URLs.")

    hypotheses = {item.strip().lower() for item in request.hypotheses if item.strip()}
    probes: list[dict] = []
    recommendations: list[str] = []

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        try:
            baseline = await client.get(request.url)
            baseline_text = baseline.text[:6000]
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Security simulation baseline failed: {exc}") from exc

        def add_probe(probe_type: str, status: str, severity: str, summary: str, evidence: list[str], request_preview: str, next_step: str):
            probes.append(
                {
                    "id": len(probes) + 1,
                    "probe_type": probe_type,
                    "status": status,
                    "severity": severity,
                    "summary": summary,
                    "evidence": evidence[:4],
                    "request_preview": request_preview,
                    "next_step": next_step,
                }
            )

        try:
            options_response = await client.options(request.url)
            allow_value = options_response.headers.get("allow", "")
            if allow_value:
                add_probe(
                    "method-discovery",
                    "signal",
                    "low",
                    "OPTIONS cevabi izinli metodlari aciga cikariyor.",
                    [f"Allow: {allow_value}"],
                    f"OPTIONS {request.url}",
                    "Beklenmeyen metodlar varsa endpoint bazli authz ve method hardening kontrolu yap.",
                )
        except Exception:
            add_probe("method-discovery", "blocked", "low", "OPTIONS probe'u tamamlanamadi.", [], f"OPTIONS {request.url}", "Sunucu method discovery'yi engelliyor olabilir; bu davranisi not et.")

        if not hypotheses or {"xss", "sql-injection"} & hypotheses:
            xss_marker = "visionqa_xss_probe_742"
            xss_url = _inject_query(request.url, "q", xss_marker)
            try:
                xss_response = await client.get(xss_url)
                reflected = xss_marker.lower() in xss_response.text.lower()
                add_probe(
                    "reflection-probe",
                    "signal" if reflected else "clean",
                    "medium" if reflected else "low",
                    "Query parametresi response govdesine yansiyor olabilir." if reflected else "Belirgin query reflection sinyali gorulmedi.",
                    [f"status={xss_response.status_code}", "marker reflected" if reflected else "marker not reflected"],
                    f"GET {xss_url}",
                    "Reflection varsa output encoding ve XSS payload varyasyonlariyla kontrollu test derinlestir.",
                )
            except Exception:
                add_probe("reflection-probe", "blocked", "low", "Reflection probe'u tamamlanamadi.", [], f"GET {xss_url}", "Uygulama query varyasyonlarini reddediyor olabilir.")

            sqli_payload = "' OR '1'='1"
            sqli_url = _inject_query(request.url, "q", sqli_payload)
            try:
                sqli_response = await client.get(sqli_url)
                sqli_text = sqli_response.text[:4000].lower()
                baseline_lower = baseline_text.lower()
                error_signals = any(token in sqli_text for token in ["sql", "syntax", "database", "query failed", "exception"])
                length_delta = abs(len(sqli_text) - len(baseline_lower))
                add_probe(
                    "sqli-probe",
                    "signal" if error_signals or length_delta > 250 else "clean",
                    "high" if error_signals else "medium" if length_delta > 250 else "low",
                    "SQLi probe'u hata izi veya davranis farki uretti." if error_signals or length_delta > 250 else "SQLi probe'unda belirgin hata izi gorulmedi.",
                    [f"status={sqli_response.status_code}", f"length_delta={length_delta}"] + (["sql-like error text"] if error_signals else []),
                    f"GET {sqli_url}",
                    "Boolean/error/time-based varyasyonlarla negatif test derinlestir; backend validation ve query sanitization'i kontrol et.",
                )
            except Exception:
                add_probe("sqli-probe", "blocked", "low", "SQLi probe'u tamamlanamadi.", [], f"GET {sqli_url}", "Uygulama query varyasyonlarini engelliyor veya timeout veriyor olabilir.")

        if not hypotheses or {"authorization-bypass", "idor-mass-assignment"} & hypotheses:
            split_parts = urlsplit(request.url)
            if any(char.isdigit() for char in split_parts.path):
                idor_path = re.sub(r"(\d+)", lambda m: str(int(m.group(1)) + 1), split_parts.path, count=1)
                idor_url = urlunsplit((split_parts.scheme, split_parts.netloc, idor_path, split_parts.query, split_parts.fragment))
                try:
                    idor_response = await client.get(idor_url)
                    suspicious = idor_response.status_code == 200 and abs(len(idor_response.text) - len(baseline_text)) < 800
                    add_probe(
                        "idor-probe",
                        "signal" if suspicious else "clean",
                        "medium" if suspicious else "low",
                        "Kaynak kimligi degistiginde benzer govde donuyor; IDOR ihtimali daha yakindan incelenmeli." if suspicious else "ID degisimi probe'unda belirgin bir object-level authz sinyali gorulmedi.",
                        [f"status={idor_response.status_code}", f"url={idor_url}"],
                        f"GET {idor_url}",
                        "Farkli rol ve kaynak sahipligiyle object-level authorization testi yap.",
                    )
                except Exception:
                    add_probe("idor-probe", "blocked", "low", "IDOR probe'u tamamlanamadi.", [], f"GET {idor_url}", "Path varyasyonu reddediliyor olabilir.")

    recommendations = list(dict.fromkeys(probe["next_step"] for probe in probes))
    signal_count = sum(1 for probe in probes if probe["status"] == "signal")
    blocked_count = sum(1 for probe in probes if probe["status"] == "blocked")
    overall_signal = "high" if signal_count >= 2 else "medium" if signal_count == 1 else "low"

    return {
        "url": request.url,
        "executed_count": len(probes) - blocked_count,
        "blocked_count": blocked_count,
        "overall_signal": overall_signal,
        "probes": probes,
        "recommendations": recommendations,
    }


@router.get("/history", response_model=list[schemas.SecurityHistoryItem])
def get_security_history(limit: int = 10, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit, 30))
    records = (
        db.query(SecurityAnalysisRecord)
        .order_by(SecurityAnalysisRecord.created_at.desc(), SecurityAnalysisRecord.id.desc())
        .limit(safe_limit)
        .all()
    )
    return [_history_item_schema(record) for record in records]


@router.get("/history/{record_id}", response_model=schemas.SecurityHistoryDetail)
def get_security_history_detail(record_id: int, db: Session = Depends(get_db)):
    record = db.query(SecurityAnalysisRecord).filter(SecurityAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Security history record not found.")
    return schemas.SecurityHistoryDetail(
        id=record.id,
        platform=record.platform,
        source_type=record.source_type,
        source_label=record.source_label,
        source_url=record.source_url,
        is_favorite=bool(((record.analysis_payload or {}).get("_history_meta") or {}).get("is_favorite", False)),
        created_at=record.created_at,
        analysis=schemas.SecurityAnalysisResponse.model_validate(record.analysis_payload),
    )


@router.patch("/history/{record_id}", response_model=schemas.SecurityHistoryItem)
def update_security_history_record(record_id: int, request: schemas.SecurityHistoryUpdateRequest, db: Session = Depends(get_db)):
    record = db.query(SecurityAnalysisRecord).filter(SecurityAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Security history record not found.")
    if request.source_label is not None:
        cleaned = request.source_label.strip()
        record.source_label = cleaned or None
    if request.is_favorite is not None:
        payload = _record_meta(record)
        payload["_history_meta"]["is_favorite"] = bool(request.is_favorite)
        record.analysis_payload = payload
    db.commit()
    db.refresh(record)
    return _history_item_schema(record)


@router.delete("/history/{record_id}", response_model=schemas.SecurityHistoryDeleteResponse)
def delete_security_history_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(SecurityAnalysisRecord).filter(SecurityAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Security history record not found.")
    db.delete(record)
    db.commit()
    return schemas.SecurityHistoryDeleteResponse(success=True)
