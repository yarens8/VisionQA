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
from core.tasks import run_uiux_image_task
from database import SessionLocal, get_db
from database.models import AnalysisJob, Project, UiuxAnalysisRecord
from core.uiux.engine import UiuxEngine


router = APIRouter(prefix="/uiux", tags=["uiux"])
engine = UiuxEngine()


def _record_meta(record: UiuxAnalysisRecord) -> dict:
    payload = dict(record.analysis_payload or {})
    meta = dict(payload.get("_history_meta") or {})
    payload["_history_meta"] = meta
    return payload


def _payload_project_id(payload: dict | None) -> int | None:
    try:
        value = (payload or {}).get("project_id")
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


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


def _save_uiux_record(db: Session, result: dict, *, source_label: str | None = None) -> None:
    try:
        record = UiuxAnalysisRecord(
            platform=result.get("platform", "web"),
            source_type="upload",
            source_label=source_label,
            overall_score=int(result.get("overall_score") or 0),
            findings_count=len(result.get("findings") or []),
            overview=result.get("overview") or "",
            analysis_payload=result,
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"UI/UX history save failed: {exc}")


def _normalize_uiux_payload(payload: dict) -> dict:
    normalized = dict(payload or {})
    overall_score = int(normalized.get("overall_score") or 100)
    normalized.setdefault("ux_score", overall_score)
    normalized.setdefault("visual_hierarchy_score", overall_score)
    normalized.setdefault("readability_score", overall_score)
    normalized.setdefault("consistency_score", int(normalized.get("layout_balance_score") or overall_score))
    normalized.setdefault("friction_score", overall_score)
    normalized.setdefault("focus_score", overall_score)
    normalized.setdefault("ai_critic_summary", "Kayit eski bir UI/UX analizinden geldigi icin AI critic ozeti varsayilan olarak dolduruldu.")
    normalized.setdefault(
        "score_summary",
        {
            "ux_score": normalized["ux_score"],
            "visual_hierarchy_score": normalized["visual_hierarchy_score"],
            "spacing_score": int(normalized.get("spacing_consistency_score") or overall_score),
            "consistency_score": normalized["consistency_score"],
            "readability_score": normalized["readability_score"],
            "friction_score": normalized["friction_score"],
            "focus_score": normalized["focus_score"],
        },
    )
    normalized.setdefault(
        "attention_prediction",
        {
            "focus_score": normalized["focus_score"],
            "primary_focus_label": "content-block",
            "attention_path": [],
            "summary": "Kayit eski bir analiz oldugu icin attention prediction varsayilan olarak gosteriliyor.",
        },
    )
    fixed_findings = []
    for finding in normalized.get("findings") or []:
        item = dict(finding)
        item.setdefault("ai_critic", item.get("description") or "")
        item.setdefault("why_this_matters", item.get("recommendation") or "")
        fixed_findings.append(item)
    normalized["findings"] = fixed_findings
    return normalized


def _history_item_schema(record: UiuxAnalysisRecord) -> schemas.UiuxHistoryItem:
    payload = record.analysis_payload or {}
    meta = (payload.get("_history_meta") or {})
    source_image_base64 = ((payload.get("artifacts") or {}).get("source_image_base64")) or None
    return schemas.UiuxHistoryItem(
        id=record.id,
        project_id=_payload_project_id(payload),
        platform=record.platform,
        source_type=record.source_type,
        source_label=record.source_label,
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


def _run_uiux_image_impl(request: schemas.UiuxAnalysisRequest, db: Session) -> dict:
    project = None
    if request.project_id is not None:
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {request.project_id}")

    result = engine.analyze_image(
        image_base64=request.image_base64,
        platform=request.platform,
    )
    if request.project_id is not None:
        result["project_id"] = request.project_id
        result["project_name"] = project.name if project else None
    source_label = f"{project.name} UI/UX screenshot analizi" if project else "Manuel screenshot analizi"
    _save_uiux_record(db, result, source_label=source_label)
    return result


async def _run_uiux_job_inline_if_still_queued(job_id: int, delay_seconds: float = 3.0) -> None:
    await asyncio.sleep(delay_seconds)
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job or job.status != "queued":
            return
        update_job_status(db, job, "running")
        try:
            request_data = schemas.UiuxAnalysisRequest(**(job.request_payload or {}))
            result = _run_uiux_image_impl(request_data, db)
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
    finally:
        db.close()


@router.post("/analyze-image", response_model=schemas.UiuxAnalysisResponse)
async def analyze_uiux_image(
    request: schemas.UiuxAnalysisRequest,
    db: Session = Depends(get_db),
):
    try:
        return _run_uiux_image_impl(request, db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"UI/UX analysis failed: {exc}") from exc


@router.post("/analyze-image-job", response_model=schemas.AnalysisJobStartResponse)
async def start_uiux_image_job(
    request: schemas.UiuxAnalysisRequest,
    db: Session = Depends(get_db),
):
    job = AnalysisJob(
        job_type="uiux_image_analysis",
        module_name="uiux",
        status="queued",
        target="Screenshot UI/UX analysis",
        request_payload=request.model_dump(mode="json"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    async_result = run_uiux_image_task.delay(job.id)
    job.celery_task_id = async_result.id
    db.commit()
    asyncio.create_task(_run_uiux_job_inline_if_still_queued(job.id))
    return schemas.AnalysisJobStartResponse(job_id=job.id, status=job.status, module_name=job.module_name, target=job.target)


@router.get("/jobs/{job_id}", response_model=schemas.AnalysisJobStatusResponse)
def get_uiux_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id, AnalysisJob.module_name == "uiux").first()
    if not job:
        raise HTTPException(status_code=404, detail="UI/UX analysis job not found.")
    return _job_status_schema(job)


@router.get("/history", response_model=list[schemas.UiuxHistoryItem])
def get_uiux_history(
    limit: int = 10,
    project_id: int | None = None,
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 30))
    query = (
        db.query(UiuxAnalysisRecord)
        .order_by(UiuxAnalysisRecord.created_at.desc(), UiuxAnalysisRecord.id.desc())
    )
    if project_id is not None:
        records = [
            record
            for record in query.limit(100).all()
            if _payload_project_id(record.analysis_payload) == project_id
        ][:safe_limit]
    else:
        records = query.limit(safe_limit).all()
    return [_history_item_schema(record) for record in records]


@router.get("/history/{record_id}", response_model=schemas.UiuxHistoryDetail)
def get_uiux_history_detail(
    record_id: int,
    db: Session = Depends(get_db),
):
    record = db.query(UiuxAnalysisRecord).filter(UiuxAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="UI/UX history record not found.")

    return schemas.UiuxHistoryDetail(
        id=record.id,
        project_id=_payload_project_id(record.analysis_payload),
        platform=record.platform,
        source_type=record.source_type,
        source_label=record.source_label,
        is_favorite=bool(((record.analysis_payload or {}).get("_history_meta") or {}).get("is_favorite", False)),
        created_at=record.created_at,
        analysis=schemas.UiuxAnalysisResponse.model_validate(_normalize_uiux_payload(record.analysis_payload)),
    )


@router.patch("/history/{record_id}", response_model=schemas.UiuxHistoryItem)
def update_uiux_history_record(
    record_id: int,
    request: schemas.UiuxHistoryUpdateRequest,
    db: Session = Depends(get_db),
):
    record = db.query(UiuxAnalysisRecord).filter(UiuxAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="UI/UX history record not found.")

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


@router.delete("/history/{record_id}", response_model=schemas.UiuxHistoryDeleteResponse)
def delete_uiux_history_record(
    record_id: int,
    db: Session = Depends(get_db),
):
    record = db.query(UiuxAnalysisRecord).filter(UiuxAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="UI/UX history record not found.")

    db.delete(record)
    db.commit()
    return schemas.UiuxHistoryDeleteResponse(success=True)
