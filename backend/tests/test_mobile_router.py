import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
from core.job_payload import to_json_payload
from database import SessionLocal
from database.models import AnalysisJob, MobileAnalysisRecord, Project
from routers import mobile_router


def test_mobile_analysis_detects_mobile_ux_signals():
    client = TestClient(main.app)
    payload = {
        "platform": "android",
        "screen_name": "Login Screen",
        "element_metadata": [
            {"element_type": "input", "x": 20, "y": 80, "width": 260, "height": 42, "text_content": "Email"},
            {"element_type": "input", "x": 20, "y": 132, "width": 260, "height": 42, "text_content": "Password"},
            {"element_type": "input", "x": 20, "y": 184, "width": 260, "height": 42, "text_content": "OTP code"},
            {"element_type": "button", "x": 20, "y": 240, "width": 38, "height": 36, "text_content": "Continue"},
            {"element_type": "button", "x": 68, "y": 240, "width": 38, "height": 36, "text_content": "Help"},
            {"element_type": "button", "x": 116, "y": 240, "width": 38, "height": 36, "text_content": "Sign up"},
            {"element_type": "button", "x": 164, "y": 240, "width": 38, "height": 36, "text_content": "Google"},
        ],
    }

    response = client.post("/mobile/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    categories = {item["category"] for item in data["findings"]}
    assert "touch-target" in categories
    assert "auth-friction" in categories
    assert "thumb-zone" in categories
    assert data["context_profile"]["screen_type"] == "auth"
    assert data["ai_mobile_critic"]
    assert data["context_playbook"]
    assert data["supported_now"]


def test_mobile_analysis_requires_some_input():
    client = TestClient(main.app)
    response = client.post("/mobile/analyze", json={"platform": "android"})
    assert response.status_code == 400


def test_mobile_analysis_job_starts_and_exposes_status(monkeypatch):
    class _FakeAsyncResult:
        id = "mobile-celery-task"

    monkeypatch.setattr(mobile_router.run_mobile_analysis_task, "delay", lambda job_id: _FakeAsyncResult())

    client = TestClient(main.app)
    response = client.post(
        "/mobile/analyze-job",
        json={
            "platform": "android",
            "screen_name": "Login Screen",
            "element_metadata": [
                {"element_type": "button", "x": 20, "y": 240, "width": 38, "height": 36, "text_content": "Continue"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["module_name"] == "mobile"

    status_response = client.get(f"/mobile/jobs/{payload['job_id']}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["job_id"] == payload["job_id"]
    assert status_payload["status"] == "queued"
    assert status_payload["celery_task_id"] == "mobile-celery-task"

    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == payload["job_id"]).first()
        assert job is not None
        db.delete(job)
        db.commit()
    finally:
        db.close()


def test_mobile_analysis_saves_history_and_reopens_record():
    client = TestClient(main.app)
    db = SessionLocal()
    try:
        project = Project(name="Mobile History Project", description="Mobile record binding", platforms=["mobile_android"])
        db.add(project)
        db.commit()
        db.refresh(project)
        project_id = project.id
    finally:
        db.close()

    response = client.post(
        "/mobile/analyze",
        json={
            "platform": "android",
            "project_id": project_id,
            "screen_name": "Checkout Screen",
            "element_metadata": [
                {"element_type": "button", "x": 20, "y": 240, "width": 38, "height": 36, "text_content": "Pay"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["record_id"]
    assert payload["project_id"] == project_id

    history_response = client.get(f"/mobile/history?project_id={project_id}")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history
    assert history[0]["id"] == payload["record_id"]
    assert history[0]["source_label"] == "Checkout Screen"

    detail_response = client.get(f"/mobile/history/{payload['record_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["analysis"]["overall_score"] == payload["overall_score"]
    assert detail["analysis"]["record_id"] == payload["record_id"]

    db = SessionLocal()
    try:
        record = db.query(MobileAnalysisRecord).filter(MobileAnalysisRecord.id == payload["record_id"]).first()
        project = db.query(Project).filter(Project.id == project_id).first()
        assert record is not None
        if record:
            db.delete(record)
        if project:
            db.delete(project)
        db.commit()
    finally:
        db.close()


def test_job_payload_accepts_dict_results():
    payload = to_json_payload({"overall_score": 91, "findings": []})

    assert payload["overall_score"] == 91
    assert payload["findings"] == []
