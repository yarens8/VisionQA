import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.job_payload import to_json_payload
from core.security.job_runner import update_job_status
from core.tasks import run_performance_analysis_task
from database import SessionLocal, get_db
from database.models import AnalysisJob, PerformanceAnalysisRecord
from core.performance.engine import PerformanceEngine
from schemas import PerformanceAnalysisResponse, PerformanceAnalyzeRequest

router = APIRouter(prefix="/performance", tags=["performance"])


def _save_performance_record(db: Session, result: PerformanceAnalysisResponse, request: PerformanceAnalyzeRequest) -> None:
    try:
        payload = to_json_payload(result)
        payload["project_id"] = request.project_id
        source_url = request.url or request.api_url
        source_type = "web" if request.url else "api" if request.api_url else "database"
        source_label = source_url or (request.db_query or "Performance analysis")[:120]
        findings = payload.get("findings") or []
        record = PerformanceAnalysisRecord(
            platform=payload.get("platform") or request.platform or "web",
            source_type=source_type,
            source_label=source_label,
            source_url=source_url,
            overall_score=int(payload.get("overall_score") or 0),
            findings_count=len(findings),
            overview=payload.get("overview"),
            analysis_payload=payload,
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"⚠️ Performance analysis history save failed: {exc}")


def _performance_history_item(record: PerformanceAnalysisRecord):
    payload = record.analysis_payload or {}
    return {
        "id": record.id,
        "platform": record.platform,
        "source_type": record.source_type,
        "source_label": record.source_label,
        "source_url": record.source_url,
        "project_id": payload.get("project_id"),
        "overall_score": record.overall_score,
        "findings_count": record.findings_count,
        "overview": record.overview,
        "performance_grade": payload.get("performance_grade"),
        "technical_score": payload.get("technical_score"),
        "perceived_score": payload.get("perceived_score"),
        "bottleneck_confidence": payload.get("bottleneck_confidence"),
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _job_status_schema(job: AnalysisJob):
    return {
        "job_id": job.id,
        "status": job.status,
        "module_name": job.module_name,
        "target": job.target,
        "celery_task_id": job.celery_task_id,
        "source_record_id": job.source_record_id,
        "error_message": job.error_message,
        "result": job.result_payload,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


async def _run_performance_analysis_impl(request: PerformanceAnalyzeRequest, db: Session) -> PerformanceAnalysisResponse:
    if not request.url and not request.api_url and not (request.db_connection_string and request.db_query):
        raise HTTPException(status_code=400, detail="At least one target (url, api_url, or db query) is required.")

    engine = PerformanceEngine()
    result = await engine.analyze(
        url=request.url,
        api_url=request.api_url,
        api_method=request.api_method,
        db_connection_string=request.db_connection_string,
        db_query=request.db_query,
        sample_api_runs=request.sample_api_runs,
        platform=request.platform,
    )
    _save_performance_record(db, result, request)
    return result


async def _run_performance_job_inline_if_still_queued(job_id: int, delay_seconds: float = 3.0) -> None:
    await asyncio.sleep(delay_seconds)
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job or job.status != "queued":
            return
        update_job_status(db, job, "running")
        try:
            request = PerformanceAnalyzeRequest(**(job.request_payload or {}))
            result = await _run_performance_analysis_impl(request, db)
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
    finally:
        db.close()


@router.get("/history")
async def get_performance_history(limit: int = 12, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit, 50))
    records = (
        db.query(PerformanceAnalysisRecord)
        .order_by(PerformanceAnalysisRecord.created_at.desc(), PerformanceAnalysisRecord.id.desc())
        .limit(safe_limit)
        .all()
    )
    return [_performance_history_item(record) for record in records]


@router.get("/history/{record_id}")
async def get_performance_history_detail(record_id: int, db: Session = Depends(get_db)):
    record = db.query(PerformanceAnalysisRecord).filter(PerformanceAnalysisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Performance analysis record not found")
    item = _performance_history_item(record)
    item["analysis_payload"] = record.analysis_payload
    return item


@router.post("/analyze", response_model=PerformanceAnalysisResponse)
async def analyze_performance(request: PerformanceAnalyzeRequest, db: Session = Depends(get_db)):
    return await _run_performance_analysis_impl(request, db)


@router.post("/analyze-job", response_model=dict)
async def start_performance_job(request: PerformanceAnalyzeRequest, db: Session = Depends(get_db)):
    target = request.url or request.api_url or (request.db_query or "Performance analysis")[:120]
    job = AnalysisJob(
        job_type="performance_analysis",
        module_name="performance",
        status="queued",
        target=target,
        request_payload=request.model_dump(mode="json"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    async_result = run_performance_analysis_task.delay(job.id)
    job.celery_task_id = async_result.id
    db.commit()
    asyncio.create_task(_run_performance_job_inline_if_still_queued(job.id))
    return {"job_id": job.id, "status": job.status, "module_name": job.module_name, "target": job.target}


@router.get("/jobs/{job_id}", response_model=dict)
async def get_performance_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id, AnalysisJob.module_name == "performance").first()
    if not job:
        raise HTTPException(status_code=404, detail="Performance analysis job not found")
    return _job_status_schema(job)
