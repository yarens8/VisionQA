import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
from core.performance.engine import PerformanceEngine, percentile
from database import SessionLocal
from database.models import AnalysisJob, PerformanceAnalysisRecord
from routers import performance_router
from routers.performance_router import _performance_history_item, _save_performance_record
from schemas import PerformanceAnalyzeRequest


def test_percentile_interpolates_values():
    assert percentile([10, 20, 30, 40], 0.5) == 25.0
    assert percentile([10, 20, 30, 40], 0.95) > 30


def test_performance_scoring_and_root_cause():
    engine = PerformanceEngine()
    findings = []
    engine._add_web_findings(
        findings,
        {
            "page_load_ms": 3200,
            "dom_content_loaded_ms": 1800,
            "fcp_ms": 2000,
            "lcp_ms": 3000,
            "tti_ms": 3400,
            "cls": 0.2,
            "transfer_kb": 512,
        },
    )
    engine._add_api_findings(
        findings,
        {
            "avg_ms": 900,
            "p50_ms": 800,
            "p95_ms": 1500,
            "p99_ms": 1800,
            "error_rate": 0.2,
            "timeout_count": 1,
            "sample_count": 5,
        },
    )
    engine._add_db_findings(
        findings,
        {
            "duration_ms": 260,
            "row_count": 5,
            "success": True,
        },
    )

    assert findings
    categories = {finding["category"] for finding in findings}
    assert "web-lcp" in categories
    assert "api-latency" in categories
    assert "db-slow-query" in categories

    root = engine._root_cause_summary(
        {"lcp_ms": 3000, "fcp_ms": 2000, "tti_ms": 3400, "cls": 0.2, "page_load_ms": 3200, "dom_content_loaded_ms": 1800, "transfer_kb": 512},
        {"avg_ms": 900, "p50_ms": 800, "p95_ms": 1500, "p99_ms": 1800, "error_rate": 0.2, "timeout_count": 1, "sample_count": 5},
        {"duration_ms": 260, "row_count": 5, "success": True},
        findings,
    )
    assert root


def test_performance_history_item_exposes_saved_analysis_summary():
    record = PerformanceAnalysisRecord(
        id=9,
        platform="web",
        source_type="web",
        source_label="https://example.com",
        source_url="https://example.com",
        overall_score=76,
        findings_count=2,
        overview="Performance summary",
        analysis_payload={
            "project_id": 44,
            "performance_grade": "B",
            "technical_score": 74,
            "perceived_score": 78,
            "bottleneck_confidence": 62,
        },
    )

    item = _performance_history_item(record)

    assert item["id"] == 9
    assert item["source_type"] == "web"
    assert item["project_id"] == 44
    assert item["overall_score"] == 76
    assert item["performance_grade"] == "B"
    assert item["findings_count"] == 2


def test_save_performance_record_accepts_engine_dict_result():
    class FakeDb:
        def __init__(self):
            self.record = None
            self.committed = False

        def add(self, record):
            self.record = record

        def commit(self):
            self.committed = True

        def rollback(self):
            raise AssertionError("rollback should not be called")

    db = FakeDb()
    result = {
        "platform": "web",
        "overall_score": 81,
        "overview": "Performance analysis summary",
        "findings": [{"id": 1, "title": "Slow API"}],
        "performance_grade": "B",
    }
    request = PerformanceAnalyzeRequest(url="https://example.com", project_id=44)

    _save_performance_record(db, result, request)

    assert db.committed
    assert db.record.source_url == "https://example.com"
    assert db.record.analysis_payload["project_id"] == 44
    assert db.record.overall_score == 81
    assert db.record.findings_count == 1


def test_performance_analysis_job_starts_and_exposes_status(monkeypatch):
    class _FakeAsyncResult:
        id = "performance-celery-task"

    monkeypatch.setattr(performance_router.run_performance_analysis_task, "delay", lambda job_id: _FakeAsyncResult())

    client = TestClient(main.app)
    response = client.post(
        "/performance/analyze-job",
        json={
            "url": "https://example.test",
            "api_url": "https://example.test/api",
            "platform": "web",
            "sample_api_runs": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["module_name"] == "performance"

    status_response = client.get(f"/performance/jobs/{payload['job_id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == payload["job_id"]
    assert status_payload["status"] == "queued"
    assert status_payload["celery_task_id"] == "performance-celery-task"

    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == payload["job_id"]).first()
        assert job is not None
        db.delete(job)
        db.commit()
    finally:
        db.close()
