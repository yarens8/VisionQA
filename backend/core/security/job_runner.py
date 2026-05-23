import base64
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from core.security.engine_v2 import SecurityEngineV2 as SecurityEngine
from database.models import AnalysisJob, SecurityAnalysisRecord
from executors.web.web_executor import WebExecutor


async def run_security_url_analysis(request_payload: dict) -> dict:
    """Collect URL evidence, screenshot the page, and run security analysis."""
    url = request_payload["url"]
    headless = bool(request_payload.get("headless", True))
    full_page = bool(request_payload.get("full_page", True))
    executor = WebExecutor(headless=headless)
    engine = SecurityEngine()
    response_headers: dict[str, str] = {}
    response_text = ""
    http_meta: dict[str, object] = {
        "source": "url",
        "url": url,
        "final_url": url,
        "status_code": None,
        "content_type": None,
        "collection_errors": [],
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
            response = await client.get(url)
            response_headers = dict(response.headers)
            content_type = response.headers.get("content-type", "")
            if "text" in content_type or "json" in content_type or "html" in content_type:
                response_text = response.text[:5000]
            http_meta.update(
                {
                    "final_url": str(response.url),
                    "status_code": response.status_code,
                    "content_type": content_type,
                }
            )
    except Exception as exc:
        http_meta["collection_errors"] = [f"http_fetch: {exc}"]

    try:
        await executor.start()
        await executor.navigate(url)
        screenshot_bytes = await executor.screenshot(full_page=full_page)
        image_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        result = await engine.analyze_image(
            image_base64=image_base64,
            platform="web",
            response_text=response_text,
            response_headers=response_headers,
            url=url,
        )
        result["scan_evidence"] = {
            **(result.get("scan_evidence") or {}),
            **http_meta,
        }
        return result
    finally:
        try:
            await executor.stop()
        except Exception:
            pass


def save_security_analysis_record(
    db: Session,
    result: dict,
    *,
    source_type: str,
    source_label: str | None = None,
    source_url: str | None = None,
) -> int:
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
    db.refresh(record)
    return int(record.id)


def update_job_status(
    db: Session,
    job: AnalysisJob,
    status: str,
    *,
    result_payload: dict | None = None,
    error_message: str | None = None,
    source_record_id: int | None = None,
) -> None:
    job.status = status
    job.updated_at = datetime.utcnow()
    if status == "running":
        job.started_at = datetime.utcnow()
    if status in {"completed", "failed", "cancelled"}:
        job.completed_at = datetime.utcnow()
    if result_payload is not None:
        job.result_payload = result_payload
    if error_message is not None:
        job.error_message = error_message
    if source_record_id is not None:
        job.source_record_id = source_record_id
    db.commit()
