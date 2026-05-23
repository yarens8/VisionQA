import base64
import io
import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from sqlalchemy.orm import Session

import schemas
from core.job_payload import to_json_payload
from core.security.job_runner import update_job_status
from core.tasks import run_accessibility_image_task, run_accessibility_url_task
from database import SessionLocal, get_db
from database.models import AccessibilityAnalysisRecord, AnalysisJob
from core.accessibility.engine import AccessibilityEngine
from executors.web.web_executor import WebExecutor


router = APIRouter(prefix="/accessibility", tags=["accessibility"])
engine = AccessibilityEngine()


def _record_meta(record: AccessibilityAnalysisRecord) -> dict:
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


def _save_accessibility_record(
    db: Session,
    result: dict,
    *,
    source_type: str,
    source_label: str | None = None,
    source_url: str | None = None,
) -> None:
    try:
        record = AccessibilityAnalysisRecord(
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
        print(f"⚠️ Accessibility history save failed: {exc}")


def _history_item_schema(record: AccessibilityAnalysisRecord) -> schemas.AccessibilityHistoryItem:
    payload = record.analysis_payload or {}
    meta = (payload.get("_history_meta") or {})
    source_image_base64 = ((payload.get("artifacts") or {}).get("source_image_base64")) or None
    return schemas.AccessibilityHistoryItem(
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


def _job_status_schema(job: AnalysisJob) -> schemas.AnalysisJobStatusResponse:
    return schemas.AnalysisJobStatusResponse(
        job_id=job.id,
        status=job.status,
        module_name=job.module_name,
        target=job.target,
        celery_task_id=job.celery_task_id,
        source_record_id=job.source_record_id,
        error_message=job.error_message,
        result=job.result_payload,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def _run_accessibility_image_impl(request: schemas.AccessibilityAnalysisRequest, db: Session) -> dict:
    result = engine.analyze_image(
        image_base64=request.image_base64,
        platform=request.platform,
        element_metadata=[item.model_dump() for item in request.element_metadata],
    )
    _save_accessibility_record(
        db,
        result,
        source_type="upload",
        source_label="Manuel screenshot analizi",
    )
    return result


async def _run_accessibility_url_impl(request: schemas.AccessibilityUrlAnalysisRequest, db: Session) -> dict:
    if request.platform != "web":
        raise ValueError("URL-based accessibility analysis is currently supported only for web.")

    executor = WebExecutor(headless=request.headless)
    try:
        await executor.start()
        await executor.navigate(request.url)
        screenshot_bytes = await executor.screenshot(full_page=request.full_page)
        element_metadata = await executor.extract_accessibility_metadata()
        image_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        result = engine.analyze_image(
            image_base64=image_base64,
            platform="web",
            element_metadata=element_metadata,
        )
        _save_accessibility_record(
            db,
            result,
            source_type="url",
            source_label="Canli URL analizi",
            source_url=request.url,
        )
        return result
    finally:
        try:
            await executor.stop()
        except Exception:
            pass


async def _run_accessibility_job_inline_if_still_queued(job_id: int, *, is_url: bool, delay_seconds: float = 3.0) -> None:
    await asyncio.sleep(delay_seconds)
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job or job.status != "queued":
            return
        update_job_status(db, job, "running")
        try:
            if is_url:
                request_data = schemas.AccessibilityUrlAnalysisRequest(**(job.request_payload or {}))
                result = await _run_accessibility_url_impl(request_data, db)
            else:
                request_data = schemas.AccessibilityAnalysisRequest(**(job.request_payload or {}))
                result = _run_accessibility_image_impl(request_data, db)
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
    finally:
        db.close()


@router.post("/analyze-image", response_model=schemas.AccessibilityAnalysisResponse)
async def analyze_accessibility_image(
    request: schemas.AccessibilityAnalysisRequest,
    db: Session = Depends(get_db),
):
    """Analyze a screenshot with a visual-first accessibility engine."""
    try:
        return _run_accessibility_image_impl(request, db)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Accessibility analysis failed: {exc}",
        ) from exc


@router.post("/analyze-url", response_model=schemas.AccessibilityAnalysisResponse)
async def analyze_accessibility_url(
    request: schemas.AccessibilityUrlAnalysisRequest,
    db: Session = Depends(get_db),
):
    """Analyze a live web page by collecting screenshot + web accessibility metadata."""
    if request.platform != "web":
        raise HTTPException(
            status_code=400,
            detail="URL-based accessibility analysis is currently supported only for web.",
        )

    try:
        return await _run_accessibility_url_impl(request, db)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Accessibility URL analysis failed: {exc}",
        ) from exc


@router.post("/analyze-image-job", response_model=schemas.AnalysisJobStartResponse)
async def start_accessibility_image_job(
    request: schemas.AccessibilityAnalysisRequest,
    db: Session = Depends(get_db),
):
    job = AnalysisJob(
        job_type="accessibility_image_analysis",
        module_name="accessibility",
        status="queued",
        target="Screenshot accessibility analysis",
        request_payload=request.model_dump(mode="json"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    async_result = run_accessibility_image_task.delay(job.id)
    job.celery_task_id = async_result.id
    db.commit()
    asyncio.create_task(_run_accessibility_job_inline_if_still_queued(job.id, is_url=False))
    return schemas.AnalysisJobStartResponse(job_id=job.id, status=job.status, module_name=job.module_name, target=job.target)


@router.post("/analyze-url-job", response_model=schemas.AnalysisJobStartResponse)
async def start_accessibility_url_job(
    request: schemas.AccessibilityUrlAnalysisRequest,
    db: Session = Depends(get_db),
):
    job = AnalysisJob(
        job_type="accessibility_url_analysis",
        module_name="accessibility",
        status="queued",
        target=request.url,
        request_payload=request.model_dump(mode="json"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    async_result = run_accessibility_url_task.delay(job.id)
    job.celery_task_id = async_result.id
    db.commit()
    asyncio.create_task(_run_accessibility_job_inline_if_still_queued(job.id, is_url=True))
    return schemas.AnalysisJobStartResponse(job_id=job.id, status=job.status, module_name=job.module_name, target=job.target)


@router.get("/jobs/{job_id}", response_model=schemas.AnalysisJobStatusResponse)
def get_accessibility_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id, AnalysisJob.module_name == "accessibility").first()
    if not job:
        raise HTTPException(status_code=404, detail="Accessibility analysis job not found.")
    return _job_status_schema(job)


@router.get("/history", response_model=list[schemas.AccessibilityHistoryItem])
def get_accessibility_history(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 30))
    records = (
        db.query(AccessibilityAnalysisRecord)
        .order_by(AccessibilityAnalysisRecord.created_at.desc(), AccessibilityAnalysisRecord.id.desc())
        .limit(safe_limit)
        .all()
    )
    return [_history_item_schema(record) for record in records]


@router.get("/history/{record_id}", response_model=schemas.AccessibilityHistoryDetail)
def get_accessibility_history_detail(
    record_id: int,
    db: Session = Depends(get_db),
):
    record = db.query(AccessibilityAnalysisRecord).filter(AccessibilityAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Accessibility history record not found.")

    return schemas.AccessibilityHistoryDetail(
        id=record.id,
        platform=record.platform,
        source_type=record.source_type,
        source_label=record.source_label,
        source_url=record.source_url,
        is_favorite=bool(((record.analysis_payload or {}).get("_history_meta") or {}).get("is_favorite", False)),
        created_at=record.created_at,
        analysis=schemas.AccessibilityAnalysisResponse.model_validate(record.analysis_payload),
    )


@router.patch("/history/{record_id}", response_model=schemas.AccessibilityHistoryItem)
def update_accessibility_history_record(
    record_id: int,
    request: schemas.AccessibilityHistoryUpdateRequest,
    db: Session = Depends(get_db),
):
    record = db.query(AccessibilityAnalysisRecord).filter(AccessibilityAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Accessibility history record not found.")

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


@router.delete("/history/{record_id}", response_model=schemas.AccessibilityHistoryDeleteResponse)
def delete_accessibility_history_record(
    record_id: int,
    db: Session = Depends(get_db),
):
    record = db.query(AccessibilityAnalysisRecord).filter(AccessibilityAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Accessibility history record not found.")

    db.delete(record)
    db.commit()
    return schemas.AccessibilityHistoryDeleteResponse(success=True)
