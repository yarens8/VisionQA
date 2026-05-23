import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.job_payload import to_json_payload
from core.security.job_runner import update_job_status
from core.tasks import run_mobile_analysis_task
from core.mobile.engine import MobileAnalysisEngine
from database import SessionLocal, get_db
from database.models import AnalysisJob, MobileAnalysisRecord
from schemas import (
    AnalysisJobStartResponse,
    AnalysisJobStatusResponse,
    MobileAnalysisRequest,
    MobileAnalysisResponse,
    MobileHistoryDetail,
    MobileHistoryItem,
)

router = APIRouter(prefix="/mobile", tags=["mobile"])


def _job_status_schema(job: AnalysisJob) -> AnalysisJobStatusResponse:
    return AnalysisJobStatusResponse(
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


def _run_mobile_analysis_impl(request: MobileAnalysisRequest) -> MobileAnalysisResponse:
    if not request.image_base64 and not request.element_metadata:
        raise ValueError("Mobil analiz icin screenshot veya element metadata gereklidir.")

    engine = MobileAnalysisEngine()
    result = engine.analyze(
        platform=request.platform,
        screen_name=request.screen_name,
        image_base64=request.image_base64,
        element_metadata=[item.model_dump() for item in request.element_metadata],
    )
    result["project_id"] = request.project_id
    return result


def _save_mobile_analysis_record(db: Session, request: MobileAnalysisRequest, result: dict) -> int:
    payload = to_json_payload(result)
    payload["project_id"] = request.project_id
    payload["source"] = {
        "platform": request.platform,
        "screen_name": request.screen_name,
        "has_screenshot": bool(request.image_base64),
        "element_count": len(request.element_metadata or []),
    }
    if request.image_base64:
        payload["image_base64"] = request.image_base64

    record = MobileAnalysisRecord(
        platform=request.platform or "android",
        source_type="screenshot" if request.image_base64 else "metadata",
        source_label=request.screen_name or f"{request.platform or 'mobile'} screen",
        overall_score=int(payload.get("overall_score") or 0),
        findings_count=len(payload.get("findings") or []),
        overview=payload.get("overview") or "",
        analysis_payload=payload,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    payload["record_id"] = record.id
    record.analysis_payload = payload
    db.commit()
    return int(record.id)


async def _run_mobile_job_inline_if_still_queued(job_id: int, delay_seconds: float = 3.0) -> None:
    await asyncio.sleep(delay_seconds)
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job or job.status != "queued":
            return
        update_job_status(db, job, "running")
        try:
            request_data = MobileAnalysisRequest(**(job.request_payload or {}))
            result = _run_mobile_analysis_impl(request_data)
            record_id = _save_mobile_analysis_record(db, request_data, result)
            result["record_id"] = record_id
            update_job_status(db, job, "completed", result_payload=to_json_payload(result), source_record_id=record_id)
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
    finally:
        db.close()


@router.post("/analyze", response_model=MobileAnalysisResponse)
def analyze_mobile(request: MobileAnalysisRequest, db: Session = Depends(get_db)):
    if not request.image_base64 and not request.element_metadata:
        raise HTTPException(
            status_code=400,
            detail="Mobil analiz icin screenshot veya element metadata gereklidir.",
        )

    try:
        result = _run_mobile_analysis_impl(request)
        record_id = _save_mobile_analysis_record(db, request, result)
        result["record_id"] = record_id
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/analyze-job", response_model=AnalysisJobStartResponse)
async def start_mobile_analysis_job(request: MobileAnalysisRequest, db: Session = Depends(get_db)):
    job = AnalysisJob(
        job_type="mobile_analysis",
        module_name="mobile",
        status="queued",
        target=request.screen_name or request.platform,
        request_payload=request.model_dump(mode="json"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    async_result = run_mobile_analysis_task.delay(job.id)
    job.celery_task_id = async_result.id
    db.commit()
    asyncio.create_task(_run_mobile_job_inline_if_still_queued(job.id))
    return AnalysisJobStartResponse(job_id=job.id, status=job.status, module_name=job.module_name, target=job.target)


@router.get("/jobs/{job_id}", response_model=AnalysisJobStatusResponse)
def get_mobile_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id, AnalysisJob.module_name == "mobile").first()
    if not job:
        raise HTTPException(status_code=404, detail="Mobile analysis job not found")
    return _job_status_schema(job)


def _mobile_history_item(record: MobileAnalysisRecord) -> MobileHistoryItem:
    payload = record.analysis_payload or {}
    context = payload.get("context_profile") or {}
    return MobileHistoryItem(
        id=record.id,
        project_id=payload.get("project_id"),
        platform=record.platform,
        source_type=record.source_type,
        source_label=record.source_label,
        overall_score=record.overall_score,
        findings_count=record.findings_count,
        overview=record.overview or "",
        screen_type=context.get("screen_type"),
        created_at=record.created_at,
    )


@router.get("/history", response_model=list[MobileHistoryItem])
def get_mobile_history(project_id: int | None = None, limit: int = 20, db: Session = Depends(get_db)):
    records = (
        db.query(MobileAnalysisRecord)
        .order_by(MobileAnalysisRecord.created_at.desc(), MobileAnalysisRecord.id.desc())
        .limit(100)
        .all()
    )
    if project_id is not None:
        records = [
            record
            for record in records
            if (record.analysis_payload or {}).get("project_id") == project_id
        ]
    return [_mobile_history_item(record) for record in records[: max(1, min(limit, 50))]]


@router.get("/history/{record_id}", response_model=MobileHistoryDetail)
def get_mobile_history_detail(record_id: int, db: Session = Depends(get_db)):
    record = db.query(MobileAnalysisRecord).filter(MobileAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Mobile analysis record not found")
    payload = record.analysis_payload or {}
    payload.setdefault("record_id", record.id)
    payload.setdefault("project_id", payload.get("project_id"))
    return MobileHistoryDetail(
        id=record.id,
        project_id=payload.get("project_id"),
        platform=record.platform,
        source_type=record.source_type,
        source_label=record.source_label,
        created_at=record.created_at,
        analysis=payload,
    )
