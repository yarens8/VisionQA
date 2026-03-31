import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main


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
