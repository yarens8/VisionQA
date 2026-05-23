import base64
import io
import os
import sys

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
from core.uiux.engine import UiuxEngine
from database import SessionLocal
from database.models import AnalysisJob, Project, UiuxAnalysisRecord
from routers import uiux_router


def _sample_uiux_image_base64() -> str:
    image = Image.new("RGB", (420, 320), "#f8fafc")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((40, 32, 210, 82), radius=14, fill="#111827")
    draw.rounded_rectangle((64, 108, 234, 158), radius=14, fill="#111827")
    draw.rounded_rectangle((40, 206, 260, 256), radius=14, fill="#111827")

    draw.rounded_rectangle((270, 108, 330, 158), radius=14, fill="#111827")
    draw.rounded_rectangle((340, 108, 400, 158), radius=14, fill="#111827")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def test_uiux_engine_returns_multiple_findings():
    engine = UiuxEngine()
    result = engine.analyze_image(_sample_uiux_image_base64())

    categories = {item["category"] for item in result["findings"]}
    assert result["platform"] == "web"
    assert result["overall_score"] < 100
    assert "alignment" in categories
    assert "spacing" in categories
    assert "consistency" in categories
    assert result["ux_score"] <= 100
    assert "ai_critic_summary" in result
    assert "attention_prediction" in result
    assert result["findings"][0]["ai_critic"]
    assert result["findings"][0]["why_this_matters"]
    assert result["findings"][0]["numeric_evidence"]["source"] == "image-processing"
    assert result["findings"][0]["test_suggestion"]
    assert result["score_breakdown"]["layout_alignment"] <= 100
    assert result["image_processing_metrics"]["visual_clutter_score"] >= 0
    assert "text" in result["image_processing_metrics"]
    assert result["image_processing_metrics"]["text"]["readability_risk_score"] >= 0
    assert result["evidence_matrix"]["candidate_count"] >= 0
    assert "readability_risk_score" in result["evidence_matrix"]
    assert result["test_suggestions"]
    assert result["artifacts"]["annotated_image_base64"]


def test_uiux_endpoint_works():
    client = TestClient(main.app)
    response = client.post(
        "/uiux/analyze-image",
        json={
            "platform": "web",
            "image_base64": _sample_uiux_image_base64(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["findings"]
    assert "image_processing_metrics" in payload
    assert "evidence_matrix" in payload
    assert payload["artifacts"]["source_image_base64"]


def test_uiux_endpoint_binds_record_to_project():
    db = SessionLocal()
    project = Project(
        name="UIUX Binding Test",
        description="Project binding test",
        platforms=["web"],
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    project_id = project.id
    db.close()

    client = TestClient(main.app)
    response = client.post(
        "/uiux/analyze-image",
        json={
            "platform": "web",
            "image_base64": _sample_uiux_image_base64(),
            "project_id": project_id,
        },
    )

    assert response.status_code == 200
    assert response.json()["project_id"] == project_id

    history_response = client.get(f"/uiux/history?project_id={project_id}")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history
    assert history[0]["project_id"] == project_id

    db = SessionLocal()
    try:
        records = [
            record
            for record in db.query(UiuxAnalysisRecord).all()
            if (record.analysis_payload or {}).get("project_id") == project_id
        ]
        for record in records:
            db.delete(record)
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            db.delete(project)
        db.commit()
    finally:
        db.close()


def test_uiux_image_job_starts_and_exposes_status(monkeypatch):
    class _FakeAsyncResult:
        id = "uiux-image-task"

    monkeypatch.setattr(uiux_router.run_uiux_image_task, "delay", lambda job_id: _FakeAsyncResult())

    client = TestClient(main.app)
    response = client.post(
        "/uiux/analyze-image-job",
        json={
            "platform": "web",
            "image_base64": _sample_uiux_image_base64(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["module_name"] == "uiux"

    status_response = client.get(f"/uiux/jobs/{payload['job_id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == payload["job_id"]
    assert status_payload["status"] == "queued"
    assert status_payload["celery_task_id"] == "uiux-image-task"

    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == payload["job_id"]).first()
        assert job is not None
        db.delete(job)
        db.commit()
    finally:
        db.close()
