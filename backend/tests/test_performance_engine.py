import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.performance.engine import PerformanceEngine, percentile


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
