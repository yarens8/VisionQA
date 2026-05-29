import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
from database import SessionLocal
from database.models import Finding, JiraTicketDraft, Page, PlatformType, Project, TestRun as DbTestRun, TestStatus as DbTestStatus


def _create_project(client: TestClient) -> int:
    response = client.post(
        "/projects",
        json={
            "name": "Case CRUD Test",
            "description": "Manual case CRUD coverage",
            "platforms": ["web"],
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_manual_case_create_update_and_delete_flow():
    client = TestClient(main.app)
    project_id = _create_project(client)

    create_response = client.post(
        f"/projects/{project_id}/cases",
        json={
            "title": "Login happy path",
            "description": "Manual smoke case",
            "category": "happy_path",
            "priority": "high",
            "steps": [
                {"order": 1, "action": "navigate", "target": "https://example.test", "expected": "Page opens"},
                {"order": 2, "action": "click", "target": "button[type='submit']", "expected": "Form submits"},
            ],
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["title"] == "Login happy path"
    assert len(created["steps"]) == 2

    update_response = client.put(
        f"/projects/cases/{created['id']}",
        json={
            "title": "Login negative path",
            "status": "approved",
            "steps": [
                {"order": 1, "action": "navigate", "target": "https://example.test/login"},
            ],
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["title"] == "Login negative path"
    assert updated["status"] == "approved"
    assert len(updated["steps"]) == 1

    delete_response = client.delete(f"/projects/cases/{created['id']}")

    assert delete_response.status_code == 204
    missing_response = client.get(f"/cases/{created['id']}")
    assert missing_response.status_code == 404


def test_manual_case_create_validates_project_and_title():
    client = TestClient(main.app)

    missing_project_response = client.post(
        "/projects/999999999/cases",
        json={"title": "Unreachable"},
    )
    assert missing_project_response.status_code == 404

    project_id = _create_project(client)
    missing_title_response = client.post(
        f"/projects/{project_id}/cases",
        json={"title": "   "},
    )
    assert missing_title_response.status_code == 400


def test_project_delete_removes_related_records():
    client = TestClient(main.app)
    project_id = _create_project(client)

    db = SessionLocal()
    try:
        page = Page(project_id=project_id, name="Delete flow", url="https://delete.example.test")
        db.add(page)
        db.flush()
        run = DbTestRun(
            project_id=project_id,
            page_id=page.id,
            platform=PlatformType.WEB,
            module_name="web",
            target=page.url,
            status=DbTestStatus.FAILED,
        )
        db.add(run)
        db.flush()
        db.add(
            Finding(
                test_run_id=run.id,
                title="Delete finding",
                description="Finding attached to deleted project",
                severity="medium",
                category="test",
            )
        )
        db.add(
            JiraTicketDraft(
                project_id=project_id,
                provider="jira",
                ticket_key="JIRA-DRAFT-DELETE",
                source_module="uiux",
                source_type="final_report_action",
                source_ref="delete-test",
                title="Delete draft",
                description="Draft attached to deleted project",
                priority="medium",
                payload={},
            )
        )
        db.commit()
    finally:
        db.close()

    delete_response = client.delete(f"/projects/{project_id}")
    assert delete_response.status_code == 204

    db = SessionLocal()
    try:
        assert db.query(Project).filter(Project.id == project_id).first() is None
        assert db.query(Page).filter(Page.project_id == project_id).count() == 0
        assert db.query(DbTestRun).filter(DbTestRun.project_id == project_id).count() == 0
        assert db.query(JiraTicketDraft).filter(JiraTicketDraft.project_id == project_id).count() == 0
    finally:
        db.close()
