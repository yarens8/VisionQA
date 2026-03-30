import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from routers.api_test_router import (
    _build_api_analysis_response,
    _detect_api_findings,
)
from routers.db_test_router import _analyze_query_text, _analyze_sample_rows
from schemas import ApiTestAnalyzeRequest


def test_api_analysis_detects_status_and_debug_findings():
    request = ApiTestAnalyzeRequest(
        method="POST",
        url="https://example.com/api/items",
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
