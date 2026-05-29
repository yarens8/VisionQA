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
    image = Image.new("RGB", (920, 520), "#f8fafc")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((72, 42, 410, 108), radius=14, fill="#111827")
    draw.rounded_rectangle((110, 156, 440, 222), radius=14, fill="#111827")
    draw.rounded_rectangle((72, 338, 510, 404), radius=14, fill="#111827")

    draw.rounded_rectangle((600, 156, 700, 222), radius=14, fill="#111827")
    draw.rounded_rectangle((735, 156, 835, 222), radius=14, fill="#111827")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _portrait_mobile_image_base64() -> str:
    image = Image.new("RGB", (390, 820), "#f8fafc")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 42, 362, 150), radius=18, fill="#2563eb")
    draw.rounded_rectangle((32, 190, 358, 252), radius=14, fill="#ffffff", outline="#cbd5e1")
    draw.rounded_rectangle((32, 270, 358, 332), radius=14, fill="#ffffff", outline="#cbd5e1")
    draw.rounded_rectangle((136, 358, 254, 394), radius=12, fill="#16a34a")
    draw.rounded_rectangle((28, 620, 92, 652), radius=10, fill="#111827")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _login_task_image_base64() -> str:
    image = Image.new("RGB", (390, 820), "#f8fafc")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((54, 78, 336, 178), radius=22, fill="#fee2e2")
    draw.rounded_rectangle((58, 250, 332, 306), radius=12, fill="#111827")
    draw.rounded_rectangle((58, 330, 332, 386), radius=12, fill="#111827")
    draw.rounded_rectangle((84, 438, 306, 492), radius=14, fill="#ef4444")
    draw.rounded_rectangle((104, 548, 286, 584), radius=12, fill="#111827")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _low_contrast_color_image_base64() -> str:
    image = Image.new("RGB", (900, 520), "#d8dde5")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 72, 820, 172), radius=18, fill="#cbd5e1")
    draw.rounded_rectangle((120, 238, 620, 300), radius=16, fill="#c7d2df")
    draw.rounded_rectangle((660, 238, 804, 300), radius=16, fill="#b9c7d8")
    draw.rounded_rectangle((120, 342, 804, 404), radius=16, fill="#cbd5e1")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _inconsistent_design_token_image_base64() -> str:
    image = Image.new("RGB", (940, 560), "#f8fafc")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((54, 46, 420, 118), radius=4, fill="#111827")
    draw.rounded_rectangle((54, 151, 396, 204), radius=22, fill="#ffffff", outline="#cbd5e1")
    draw.rounded_rectangle((54, 221, 460, 288), radius=8, fill="#ffffff", outline="#cbd5e1")
    draw.rounded_rectangle((54, 336, 244, 376), radius=18, fill="#2563eb")
    draw.rounded_rectangle((272, 336, 438, 392), radius=4, fill="#0f172a")
    draw.rounded_rectangle((600, 68, 860, 130), radius=28, fill="#e2e8f0")
    draw.rounded_rectangle((600, 171, 832, 225), radius=2, fill="#e2e8f0")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def test_uiux_engine_returns_multiple_findings():
    engine = UiuxEngine()
    result = engine.analyze_image(_sample_uiux_image_base64(), platform="auto")

    categories = {item["category"] for item in result["findings"]}
    assert result["platform"] == "web"
    assert result["requested_platform"] == "auto"
    assert result["detected_platform"] == "web"
    assert result["platform_profile"]
    assert result["platform_rules_applied"]
    assert result["overall_score"] < 100
    assert len(categories) >= 3
    assert categories.intersection({"alignment", "spacing", "consistency", "hierarchy", "section-separation"})
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
    assert "design_tokens" in result["image_processing_metrics"]
    assert result["design_tokens"]["design_token_score"] >= 0
    assert result["evidence_matrix"]["candidate_count"] >= 0
    assert "readability_risk_score" in result["evidence_matrix"]
    assert "design_token_score" in result["evidence_matrix"]
    assert result["task_evaluation"]["task_type"] in {"navigation", "generic", "search", "login", "form", "checkout"}
    assert "task_completion_score" in result["score_breakdown"]
    assert "persona_risk" in result
    assert result["persona_risk"]["personas"]
    assert "persona_risk_score" in result["score_breakdown"]
    assert "highest_risk_persona" in result["evidence_matrix"]
    assert result["test_suggestions"]
    assert result["artifacts"]["annotated_image_base64"]


def test_uiux_engine_reports_color_intelligence():
    engine = UiuxEngine()
    result = engine.analyze_image(_low_contrast_color_image_base64(), platform="web")

    color = result["color_intelligence"]
    categories = {item["category"] for item in result["findings"]}
    assert color["dominant_palette"]
    assert color["dominant_contrast_ratio"] < 3
    assert color["palette_consistency_score"] <= 100
    assert color["cta_visibility_score"] <= 100
    assert color["suggested_palette"]
    assert color["recommendation"]
    assert categories.intersection({"contrast-risk", "cta-visibility", "palette-consistency", "color-harmony"})
    assert result["evidence_matrix"]["recommended_text_color"]


def test_uiux_engine_reports_design_token_consistency():
    engine = UiuxEngine()
    result = engine.analyze_image(_inconsistent_design_token_image_base64(), platform="web")

    tokens = result["design_tokens"]
    categories = {item["category"] for item in result["findings"]}
    assert tokens["design_token_score"] <= 100
    assert tokens["spacing_tokens"]
    assert "spacing_token_fit_score" in tokens
    assert "font_scale_score" in tokens
    assert "radius_consistency_score" in tokens
    assert "button_consistency_score" in tokens
    assert categories.intersection({"spacing-token", "font-scale", "radius-consistency", "button-consistency"})
    assert result["score_breakdown"]["design_token_consistency"] == tokens["design_token_score"]


def test_uiux_engine_auto_detects_mobile_profile():
    engine = UiuxEngine()
    result = engine.analyze_image(_portrait_mobile_image_base64(), platform="auto")

    categories = {item["category"] for item in result["findings"]}
    assert result["platform"] == "mobile"
    assert result["requested_platform"] == "auto"
    assert result["detected_platform"] == "mobile"
    assert result["platform_confidence"] >= 80
    assert "touch-target" in result["platform_rules_applied"]
    assert any(category.startswith("mobile-") for category in categories)
    assert result["evidence_matrix"]["detected_platform"] == "mobile"


def test_uiux_engine_respects_forced_mobile_profile():
    engine = UiuxEngine()
    result = engine.analyze_image(_sample_uiux_image_base64(), platform="mobile")

    assert result["platform"] == "mobile"
    assert result["requested_platform"] == "mobile"
    assert result["detected_platform"] == "mobile"
    assert result["platform_profile"] == "mobile-forced"


def test_uiux_engine_reports_task_based_evaluation_for_login_like_screen():
    engine = UiuxEngine()
    result = engine.analyze_image(_login_task_image_base64(), platform="mobile")

    task = result["task_evaluation"]
    categories = {item["category"] for item in result["findings"]}
    assert task["task_type"] == "login"
    assert task["task_score"] <= 100
    assert task["checks"]
    assert result["evidence_matrix"]["task_type"] == task["task_type"]
    assert result["score_breakdown"]["task_completion_score"] == task["task_score"]
    assert "task-flow" in categories or task["task_score"] >= 82


def test_uiux_engine_reports_persona_based_risk():
    engine = UiuxEngine()
    result = engine.analyze_image(_login_task_image_base64(), platform="mobile")

    persona = result["persona_risk"]
    categories = {item["category"] for item in result["findings"]}
    persona_ids = {item["id"] for item in persona["personas"]}
    assert {"low_vision", "mobile_one_hand", "novice_user", "screen_reader_user"}.issubset(persona_ids)
    assert persona["overall_persona_risk"] >= 0
    assert persona["highest_risk_persona"]["id"] in persona_ids
    assert result["evidence_matrix"]["persona_risk_score"] == persona["overall_persona_risk"]
    assert "persona-risk" in categories or persona["overall_persona_risk"] < 48


def test_uiux_endpoint_works():
    client = TestClient(main.app)
    response = client.post(
        "/uiux/analyze-image",
        json={
            "platform": "auto",
            "image_base64": _sample_uiux_image_base64(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["findings"]
    assert payload["detected_platform"] == "web"
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
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["visual_regression"]["status"] == "no_baseline"

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


def test_uiux_endpoint_compares_project_against_previous_baseline():
    db = SessionLocal()
    project = Project(
        name="UIUX Regression Test",
        description="Project regression test",
        platforms=["web"],
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    project_id = project.id
    db.close()

    client = TestClient(main.app)
    first_response = client.post(
        "/uiux/analyze-image",
        json={
            "platform": "web",
            "image_base64": _sample_uiux_image_base64(),
            "project_id": project_id,
        },
    )
    second_response = client.post(
        "/uiux/analyze-image",
        json={
            "platform": "web",
            "image_base64": _inconsistent_design_token_image_base64(),
            "project_id": project_id,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    regression = second_response.json()["visual_regression"]
    assert regression["baseline_record_id"] is not None
    assert regression["status"] in {"stable", "changed", "improved", "regressed"}
    assert regression["previous_score"] is not None
    assert regression["score_delta"] is not None
    assert "pixel_change_percent" in regression

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
