import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import main
from database import SessionLocal
from routers.api_test_router import (
    _build_api_analysis_response,
    _api_history_item,
    _detect_api_findings,
)
from database.models import AnalysisJob, ApiAnalysisRecord, DbAnalysisRecord
from routers import api_test_router, db_test_router
from routers.db_test_router import _analyze_query_text, _analyze_sample_rows, _db_history_item
from schemas import ApiTestAnalyzeRequest


def test_api_analysis_detects_status_and_debug_findings():
    request = ApiTestAnalyzeRequest(
        method="POST",
        url="https://example.com/api/items",
        project_id=42,
        body={"name": "demo"},
        expected_status=201,
        expected_fields=["id", "status"],
        expected_response_type="application/json",
    )
    raw = {
        "success": True,
        "status_code": 500,
        "duration_ms": 1800,
        "response_body": "Traceback: SQLSTATE syntax error near SELECT",
        "headers": {"content-type": "text/html"},
    }

    findings = _detect_api_findings(request, raw)
    response = _build_api_analysis_response(request, raw, findings, [])

    categories = {finding.category for finding in findings}
    assert "server-error" in categories
    assert "status-mismatch" in categories
    assert "slow-response" in categories
    assert "error-leakage" in categories
    assert "response-type" in categories
    assert response.overall_score < 100
    assert response.endpoint_risk_score > 0
    assert response.ai_failure_explanation
    assert response.generated_tests
    assert response.score_breakdown.health < 100
    assert response.project_id == 42
    assert response.evidence_summary.contract_signals >= 2
    assert response.evidence_summary.security_signals >= 1
    assert "server-error" in response.evidence_summary.primary_categories


def test_db_query_analysis_flags_risky_patterns_and_duplicates():
    findings = []
    _analyze_query_text("SELECT * FROM projects", findings)
    _analyze_sample_rows(
        [
            {"id": 1, "name": None, "status": "completed", "payment_status": "pending", "password": "plain123"},
            {"id": 1, "name": None, "status": "completed", "payment_status": "pending", "password": "plain123"},
            {"id": 2, "name": "VisionQA", "status": "new", "payment_status": "paid", "password": "plain123"},
        ],
        findings,
    )

    categories = {finding.category for finding in findings}
    assert "query-shape" in categories
    assert "query-scope" in categories
    assert "duplicate-identifier" in categories
    assert "null-density" in categories
    assert "business-rule" in categories
    assert "security-storage" in categories


def test_api_history_item_exposes_saved_analysis_summary():
    record = ApiAnalysisRecord(
        id=7,
        platform="api",
        source_type="endpoint",
        source_label="GET https://example.com/api/items",
        source_url="https://example.com/api/items",
        overall_score=82,
        findings_count=1,
        overview="API analizi tamamlandi.",
        analysis_payload={
            "project_id": 12,
            "method": "GET",
            "success": True,
            "status_code": 200,
            "duration_ms": 91.4,
            "endpoint_context": "generic",
        },
    )

    item = _api_history_item(record)

    assert item["id"] == 7
    assert item["method"] == "GET"
    assert item["project_id"] == 12
    assert item["status_code"] == 200
    assert item["duration_ms"] == 91.4
    assert item["findings_count"] == 1


def test_api_analysis_job_starts_and_exposes_status(monkeypatch):
    class _FakeAsyncResult:
        id = "api-celery-task"

    monkeypatch.setattr(api_test_router.run_api_analysis_task, "delay", lambda job_id: _FakeAsyncResult())

    client = TestClient(main.app)
    response = client.post(
        "/api-test/analyze-job",
        json={
            "method": "GET",
            "url": "https://example.test/api/items",
            "expected_status": 200,
            "expected_fields": ["id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["module_name"] == "api"

    status_response = client.get(f"/api-test/jobs/{payload['job_id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == payload["job_id"]
    assert status_payload["status"] == "queued"
    assert status_payload["celery_task_id"] == "api-celery-task"

    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == payload["job_id"]).first()
        assert job is not None
        db.delete(job)
        db.commit()
    finally:
        db.close()


def test_db_history_item_exposes_saved_quality_summary():
    record = DbAnalysisRecord(
        id=11,
        platform="database",
        source_type="query",
        source_label="SELECT * FROM projects LIMIT 5",
        overall_score=88,
        findings_count=2,
        overview="DB quality summary",
        analysis_payload={
            "success": True,
            "table_name": None,
            "table_quality_score": 92,
            "duration_ms": 42.5,
            "detected_columns": ["id", "name"],
        },
    )

    item = _db_history_item(record)

    assert item["id"] == 11
    assert item["source_type"] == "query"
    assert item["overall_score"] == 88
    assert item["table_quality_score"] == 92
    assert item["detected_columns_count"] == 2


def test_db_quality_job_starts_and_exposes_status(monkeypatch):
    class _FakeAsyncResult:
        id = "db-celery-task"

    monkeypatch.setattr(db_test_router.run_db_quality_task, "delay", lambda job_id: _FakeAsyncResult())

    client = TestClient(main.app)
    response = client.post(
        "/db-test/quality-audit-job",
        json={
            "connection_string": "sqlite:///./visionqa_test.db",
            "query": "SELECT 1 AS id",
            "expected_columns": ["id"],
            "api_expected_fields": ["id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["module_name"] == "database"

    status_response = client.get(f"/db-test/jobs/{payload['job_id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == payload["job_id"]
    assert status_payload["status"] == "queued"
    assert status_payload["celery_task_id"] == "db-celery-task"

    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == payload["job_id"]).first()
        assert job is not None
        db.delete(job)
        db.commit()
    finally:
        db.close()
