import asyncio

from core.celery_app import celery_app
from core.job_payload import to_json_payload
from core.security.job_runner import run_security_url_analysis, save_security_analysis_record, update_job_status
from database import SessionLocal
from database.models import AnalysisJob


@celery_app.task(name="visionqa.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="visionqa.add")
def add(x: int, y: int) -> int:
    return x + y


@celery_app.task(name="visionqa.security.analyze_url")
def run_security_url_analysis_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Analysis job not found"}
        if job.status != "queued":
            return {"job_id": job_id, "status": job.status}

        update_job_status(db, job, "running")
        try:
            result = asyncio.run(run_security_url_analysis(job.request_payload or {}))
            record_id = save_security_analysis_record(
                db,
                result,
                source_type="url",
                source_label="Canli security URL analizi",
                source_url=(job.request_payload or {}).get("url"),
            )
            update_job_status(db, job, "completed", result_payload=to_json_payload(result), source_record_id=record_id)
            return {"job_id": job_id, "status": "completed", "record_id": record_id}
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="visionqa.dataset.analyze")
def run_dataset_analysis_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Analysis job not found"}
        if job.status != "queued":
            return {"job_id": job_id, "status": job.status}

        update_job_status(db, job, "running")
        try:
            from routers.dataset_router import _analyze_dataset_impl

            result = _analyze_dataset_impl(
                job.request_payload or {},
                db=db,
                source_type="json",
                source_label=(job.request_payload or {}).get("dataset_name") or "dataset.json",
            )
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
            return {"job_id": job_id, "status": "completed"}
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="visionqa.api.analyze")
def run_api_analysis_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Analysis job not found"}
        if job.status != "queued":
            return {"job_id": job_id, "status": job.status}

        update_job_status(db, job, "running")
        try:
            from schemas import ApiTestAnalyzeRequest
            from routers.api_test_router import _run_api_analysis_impl

            request_data = ApiTestAnalyzeRequest(**(job.request_payload or {}))
            result = asyncio.run(_run_api_analysis_impl(request_data, db))
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
            return {"job_id": job_id, "status": "completed"}
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="visionqa.database.quality_audit")
def run_db_quality_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Analysis job not found"}
        if job.status != "queued":
            return {"job_id": job_id, "status": job.status}

        update_job_status(db, job, "running")
        try:
            from schemas import DbQualityRequest
            from routers.db_test_router import _run_db_quality_impl

            request_data = DbQualityRequest(**(job.request_payload or {}))
            result = _run_db_quality_impl(request_data, db)
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
            return {"job_id": job_id, "status": "completed"}
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="visionqa.performance.analyze")
def run_performance_analysis_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Analysis job not found"}
        if job.status != "queued":
            return {"job_id": job_id, "status": job.status}

        update_job_status(db, job, "running")
        try:
            from schemas import PerformanceAnalyzeRequest
            from routers.performance_router import _run_performance_analysis_impl

            request_data = PerformanceAnalyzeRequest(**(job.request_payload or {}))
            result = asyncio.run(_run_performance_analysis_impl(request_data, db))
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
            return {"job_id": job_id, "status": "completed"}
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="visionqa.accessibility.analyze_image")
def run_accessibility_image_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Analysis job not found"}
        if job.status != "queued":
            return {"job_id": job_id, "status": job.status}

        update_job_status(db, job, "running")
        try:
            from schemas import AccessibilityAnalysisRequest
            from routers.accessibility_router import _run_accessibility_image_impl

            request_data = AccessibilityAnalysisRequest(**(job.request_payload or {}))
            result = _run_accessibility_image_impl(request_data, db)
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
            return {"job_id": job_id, "status": "completed"}
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="visionqa.accessibility.analyze_url")
def run_accessibility_url_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Analysis job not found"}
        if job.status != "queued":
            return {"job_id": job_id, "status": job.status}

        update_job_status(db, job, "running")
        try:
            from schemas import AccessibilityUrlAnalysisRequest
            from routers.accessibility_router import _run_accessibility_url_impl

            request_data = AccessibilityUrlAnalysisRequest(**(job.request_payload or {}))
            result = asyncio.run(_run_accessibility_url_impl(request_data, db))
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
            return {"job_id": job_id, "status": "completed"}
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="visionqa.uiux.analyze_image")
def run_uiux_image_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Analysis job not found"}
        if job.status != "queued":
            return {"job_id": job_id, "status": job.status}

        update_job_status(db, job, "running")
        try:
            from schemas import UiuxAnalysisRequest
            from routers.uiux_router import _run_uiux_image_impl

            request_data = UiuxAnalysisRequest(**(job.request_payload or {}))
            result = _run_uiux_image_impl(request_data, db)
            update_job_status(db, job, "completed", result_payload=to_json_payload(result))
            return {"job_id": job_id, "status": "completed"}
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="visionqa.mobile.analyze")
def run_mobile_analysis_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Analysis job not found"}
        if job.status != "queued":
            return {"job_id": job_id, "status": job.status}

        update_job_status(db, job, "running")
        try:
            from schemas import MobileAnalysisRequest
            from routers.mobile_router import _run_mobile_analysis_impl, _save_mobile_analysis_record

            request_data = MobileAnalysisRequest(**(job.request_payload or {}))
            result = _run_mobile_analysis_impl(request_data)
            record_id = _save_mobile_analysis_record(db, request_data, result)
            result["record_id"] = record_id
            update_job_status(db, job, "completed", result_payload=to_json_payload(result), source_record_id=record_id)
            return {"job_id": job_id, "status": "completed", "record_id": record_id}
        except Exception as exc:
            update_job_status(db, job, "failed", error_message=str(exc))
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()
