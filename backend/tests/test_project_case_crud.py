import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main


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
