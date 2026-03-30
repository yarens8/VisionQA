import base64
import io
import os
import sys

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
from core.uiux.engine import UiuxEngine


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
    assert payload["artifacts"]["source_image_base64"]
