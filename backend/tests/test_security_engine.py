import base64
import io
import os
import sys

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
from core.security.engine import SecurityEngine
from core.security.engine_v2 import SecurityEngineV2
from database import SessionLocal
from database.models import AnalysisJob
from routers import security_router


def _sample_security_image_base64() -> str:
    image = Image.new("RGB", (420, 220), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 20, 390, 70), fill="#fef2f2")
    draw.text((36, 34), "Traceback TypeError line 42", fill="#991b1b")
    draw.rectangle((24, 92, 390, 150), fill="#eff6ff")
    draw.text((36, 112), "admin@example.com +90 555 123 4567", fill="#1d4ed8")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def test_security_engine_finds_debug_and_pii_signals():
    result = SecurityEngine().analyze_image(_sample_security_image_base64())
    categories = {item["category"] for item in result["findings"]}
    assert "stack-trace" in categories
    assert ("email-exposure" in categories) or ("phone-exposure" in categories)
    assert "visual" in result["layer_summary"]
    assert isinstance(result["attack_hypotheses"], list)
    if result["attack_hypotheses"]:
        assert result["attack_hypotheses"][0]["playbook_steps"]
        assert "priority" in result["attack_hypotheses"][0]
        assert "payload_families" in result["attack_hypotheses"][0]
        assert "role_scenarios" in result["attack_hypotheses"][0]
    assert "context_profile" in result
    assert "cross_module_hints" in result


@pytest.mark.asyncio
async def test_security_engine_v2_adds_scan_evidence_and_surface_crops():
    result = await SecurityEngineV2().analyze_image(
        _sample_security_image_base64(),
        url="http://example.test/login",
        response_headers={"server": "test"},
        response_text="wrong password",
    )

    assert result["scan_evidence"]["source"] == "url"
    assert result["scan_evidence"]["headers_observed"] == 1
    assert result["scan_evidence"]["security_headers_checked"] >= 4
    assert "ocr" in result["scan_evidence"]["checks_executed"]
    assert result["risk_summary"]["total"] >= 1
    assert result["risk_summary"]["priority_actions"]
    assert result["surface_findings"]
    assert all(item["bounding_box"]["width"] > 0 for item in result["surface_findings"])
    assert all(item["crop_image_base64"] for item in result["surface_findings"])


def test_security_endpoint_works():
    client = TestClient(main.app)
    response = client.post("/security/analyze-image", json={"platform": "web", "image_base64": _sample_security_image_base64()})
    assert response.status_code == 200
    payload = response.json()
    assert payload["findings"]
    assert "visual_findings" in payload
    assert "attack_hypotheses" in payload
    assert "root_causes" in payload
    assert "context_profile" in payload
    assert "cross_module_hints" in payload
    assert payload["scan_evidence"]["source"] == "image"
    assert payload["scan_evidence"]["checks_executed"]
    assert "risk_summary" in payload
    assert isinstance(payload["risk_summary"]["priority_actions"], list)
    assert payload["artifacts"]["source_image_base64"]


def test_security_url_job_starts_and_exposes_status(monkeypatch):
    class _FakeAsyncResult:
        id = "celery-test-task"

    monkeypatch.setattr(security_router.run_security_url_analysis_task, "delay", lambda job_id: _FakeAsyncResult())

    client = TestClient(main.app)
    response = client.post(
        "/security/analyze-url-job",
        json={"url": "https://example.test", "platform": "web", "headless": True, "full_page": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["module_name"] == "security"

    status_response = client.get(f"/security/jobs/{payload['job_id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == payload["job_id"]
    assert status_payload["status"] == "queued"
    assert status_payload["celery_task_id"] == "celery-test-task"

    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == payload["job_id"]).first()
        assert job is not None
        db.delete(job)
        db.commit()
    finally:
        db.close()
