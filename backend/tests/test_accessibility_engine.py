import base64
import io
import os
import sys

from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.accessibility.engine import (
    AccessibilityEngine,
    _build_dino_candidates,
    ComponentCandidate,
    _apply_metadata_hints,
    _apply_detected_labels,
    _apply_text_hints,
    _build_text_region_candidates,
    _crop_to_base64,
    _classify_component,
    _component_display_name,
    _group_ocr_word_regions,
    _prune_fragment_icon_candidates,
    _prune_container_candidates,
    contrast_ratio,
)
import main


def _sample_image_base64() -> str:
    image = Image.new("RGB", (240, 140), "#f5f5f5")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 220, 65), fill="#ffffff")
    draw.rectangle((20, 80, 220, 120), fill="#ffefe8")
    draw.text((30, 30), "Low contrast hint", fill="#d0d0d0")
    draw.text((30, 90), "Primary action", fill="#ffb08a")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _form_panel_image_base64() -> str:
    image = Image.new("RGB", (420, 260), "#6c44db")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((240, 36, 390, 150), radius=12, fill="#ffffff")
    draw.rectangle((255, 60, 375, 84), fill="#f3f4f6")
    draw.rectangle((255, 95, 375, 125), fill="#ffcc18")
    draw.text((270, 102), "Devam et", fill="#947089")

    for index in range(6):
        left = 28 + index * 54
        draw.rounded_rectangle((left, 208, left + 26, 234), radius=6, fill="#ffffff")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def test_contrast_ratio_reference_values():
    assert round(contrast_ratio((0, 0, 0), (255, 255, 255)), 2) == 21.0


def test_accessibility_engine_returns_findings():
    engine = AccessibilityEngine()
    result = engine.analyze_image(_sample_image_base64())

    assert result["platform"] == "web"
    assert result["overall_score"] >= 0
    assert len(result["heatmap"]) > 0
    assert "wcag_summary" in result
    assert result["artifacts"]["overlay_image_base64"]
    assert len(result["palette"]) > 0
    assert len(result["components"]) > 0


def test_accessibility_endpoint_works():
    client = TestClient(main.app)
    response = client.post(
        "/accessibility/analyze-image",
        json={
            "platform": "web",
            "image_base64": _sample_image_base64(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "findings" in payload
    assert "overall_score" in payload
    assert payload["artifacts"]["source_image_base64"]


def test_crop_to_base64_handles_offscreen_metadata_boxes():
    image = Image.new("RGB", (120, 80), "#ffffff")

    cropped = _crop_to_base64(
        image=image,
        x=180,
        y=24,
        width=40,
        height=24,
    )

    assert cropped


def test_accessibility_url_endpoint_works_with_web_metadata(monkeypatch):
    sample_png = base64.b64decode(_sample_image_base64())

    class FakeWebExecutor:
        def __init__(self, headless=True):
            self.headless = headless

        async def start(self):
            return None

        async def navigate(self, url: str):
            return None

        async def screenshot(self, full_page: bool = True):
            return sample_png

        async def extract_accessibility_metadata(self):
            return [
                {
                    "element_type": "image",
                    "x": 20,
                    "y": 20,
                    "width": 60,
                    "height": 60,
                    "alt_text": "",
                },
                {
                    "element_type": "button",
                    "x": 120,
                    "y": 20,
                    "width": 60,
                    "height": 40,
                    "keyboard_focusable": False,
                },
            ]

        async def stop(self):
            return None

    monkeypatch.setattr("routers.accessibility_router.WebExecutor", FakeWebExecutor)

    client = TestClient(main.app)
    response = client.post(
        "/accessibility/analyze-url",
        json={
            "url": "https://example.com",
            "platform": "web",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    categories = {item["category"] for item in payload["findings"]}
    assert payload["artifacts"]["source_image_base64"]
    assert "alt-text" in categories
    assert "keyboard-navigation" in categories


def test_accessibility_history_is_saved_and_can_be_loaded():
    client = TestClient(main.app)

    analyze_response = client.post(
        "/accessibility/analyze-image",
        json={
            "platform": "web",
            "image_base64": _sample_image_base64(),
        },
    )
    assert analyze_response.status_code == 200

    history_response = client.get("/accessibility/history", params={"limit": 5})
    assert history_response.status_code == 200
    items = history_response.json()
    assert items

    latest = items[0]
    assert latest["source_type"] in {"upload", "url"}
    assert "thumbnail_base64" in latest

    detail_response = client.get(f"/accessibility/history/{latest['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["analysis"]["artifacts"]["source_image_base64"]
    assert detail["analysis"]["overview"]


def test_accessibility_history_can_be_updated_and_deleted():
    client = TestClient(main.app)

    analyze_response = client.post(
        "/accessibility/analyze-image",
        json={
            "platform": "web",
            "image_base64": _sample_image_base64(),
        },
    )
    assert analyze_response.status_code == 200

    history_response = client.get("/accessibility/history", params={"limit": 1})
    assert history_response.status_code == 200
    latest = history_response.json()[0]

    update_response = client.patch(
        f"/accessibility/history/{latest['id']}",
        json={
            "source_label": "Benim kaydim",
            "is_favorite": True,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["source_label"] == "Benim kaydim"
    assert updated["is_favorite"] is True

    delete_response = client.delete(f"/accessibility/history/{latest['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True


def test_accessibility_prioritizes_form_area_over_footer_icons():
    engine = AccessibilityEngine()
    result = engine.analyze_image(_form_panel_image_base64())

    assert result["findings"]
    first_title = result["findings"][0]["title"]
    assert ("form" in first_title) or ("panel" in first_title) or ("aksiyon butonu" in first_title)


def test_accessibility_reports_small_touch_targets():
    image = Image.new("RGB", (240, 160), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((20, 20, 55, 50), radius=8, fill="#ffcc18")
    draw.rounded_rectangle((80, 20, 120, 48), radius=8, fill="#f3f4f6")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    engine = AccessibilityEngine()
    result = engine.analyze_image(image_base64)

    touch_findings = [item for item in result["findings"] if item["category"] == "touch-target"]
    assert touch_findings
    assert "dokunma alani" in touch_findings[0]["title"]


def test_group_ocr_word_regions_merges_words_on_same_line():
    grouped = _group_ocr_word_regions(
        [
            {
                "box": [10, 12, 42, 28],
                "text": "Sign",
                "score": 0.91,
                "source": "ocr",
                "block_num": 1,
                "par_num": 1,
                "line_num": 1,
            },
            {
                "box": [50, 12, 72, 28],
                "text": "In",
                "score": 0.89,
                "source": "ocr",
                "block_num": 1,
                "par_num": 1,
                "line_num": 1,
            },
        ]
    )

    assert len(grouped) == 1
    assert grouped[0]["text"] == "Sign In"


def test_touch_target_finds_small_high_contrast_icon():
    image = Image.new("RGB", (240, 160), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.ellipse((180, 20, 205, 45), fill="#111111")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    engine = AccessibilityEngine()
    result = engine.analyze_image(image_base64)

    touch_findings = [item for item in result["findings"] if item["category"] == "touch-target"]
    assert touch_findings


def test_small_icon_is_classified_as_icon_candidate():
    label, _ = _classify_component(
        x=0,
        y=0,
        width=20,
        height=20,
        ratio=10,
        distance=200,
        pixel_density=0.7,
        cluster_size=1,
        image_width=400,
        image_height=800,
    )
    assert label == "icon-or-badge"


def test_focus_visibility_findings_are_reported():
    image = Image.new("RGB", (260, 180), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((40, 40, 180, 84), radius=10, outline="#d8d8d8", width=2, fill="#ffffff")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    engine = AccessibilityEngine()
    result = engine.analyze_image(image_base64)

    focus_findings = [item for item in result["findings"] if item["category"] == "focus-visibility"]
    assert focus_findings


def test_alt_text_and_keyboard_findings_are_reported_from_metadata():
    image = Image.new("RGB", (240, 160), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 80, 80), fill="#d9d9d9")
    draw.rounded_rectangle((120, 20, 180, 60), radius=8, fill="#ffcc18")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    engine = AccessibilityEngine()
    result = engine.analyze_image(
        image_base64,
        element_metadata=[
            {
                "element_type": "image",
                "x": 20,
                "y": 20,
                "width": 60,
                "height": 60,
                "alt_text": "",
            },
            {
                "element_type": "button",
                "x": 120,
                "y": 20,
                "width": 60,
                "height": 40,
                "keyboard_focusable": False,
            },
        ],
    )

    categories = {item["category"] for item in result["findings"]}
    assert "alt-text" in categories
    assert "keyboard-navigation" in categories


def test_dino_labels_can_upgrade_component_classification():
    candidates = [
        ComponentCandidate(
            x=100,
            y=40,
            width=120,
            height=48,
            label="content-block",
            confidence=0.5,
            contrast_ratio=4.2,
            dominant_dark="#333333",
            dominant_light="#ffffff",
            severity="medium",
            description="test",
            pixel_density=0.4,
            cluster_size=1,
        )
    ]

    relabeled = _apply_detected_labels(
        candidates,
        [{"label": "button", "score": 0.91, "box": [95, 35, 225, 95]}],
    )

    assert relabeled[0].label == "action-button"


def test_detected_labels_do_not_downgrade_text_candidates_to_icons():
    candidates = [
        ComponentCandidate(
            x=120,
            y=60,
            width=120,
            height=28,
            label="small-text",
            confidence=0.74,
            contrast_ratio=4.8,
            dominant_dark="#666666",
            dominant_light="#ffffff",
            severity="low",
            description="helper",
            pixel_density=0.18,
            cluster_size=1,
            text_hint="Forgot password",
            text_region_count=1,
        )
    ]

    relabeled = _apply_detected_labels(
        candidates,
        [{"label": "icon", "score": 0.93, "box": [116, 56, 246, 92]}],
    )

    assert relabeled[0].label == "small-text"
    assert relabeled[0].text_hint == "Forgot password"


def test_text_hints_can_upgrade_generic_component_to_action_button():
    candidates = [
        ComponentCandidate(
            x=24,
            y=32,
            width=180,
            height=28,
            label="content-block",
            confidence=0.5,
            contrast_ratio=4.1,
            dominant_dark="#333333",
            dominant_light="#ffffff",
            severity="medium",
            description="test",
            pixel_density=0.24,
            cluster_size=1,
        )
    ]

    upgraded = _apply_text_hints(
        candidates,
        [{"box": [28, 36, 196, 58], "text": "SIGN IN", "score": 0.94, "source": "ocr"}],
    )

    assert upgraded[0].label == "action-button"
    assert upgraded[0].text_hint == "SIGN IN"
    assert "SIGN IN" in _component_display_name(upgraded[0], 320, 180)


def test_text_region_candidates_can_infer_action_button_role():
    image = Image.new("RGB", (320, 180), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((40, 56, 220, 104), radius=10, fill="#6c44db")
    draw.text((96, 72), "SIGN IN", fill="#ffffff")

    candidates = _build_text_region_candidates(
        image,
        [{"box": [48, 64, 212, 98], "text": "SIGN IN", "score": 0.91, "source": "ocr"}],
    )

    assert candidates
    assert candidates[0].label == "action-button"
    assert candidates[0].text_hint == "SIGN IN"


def test_text_region_candidates_can_infer_heading_role():
    image = Image.new("RGB", (420, 220), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.text((56, 44), "Welcome back", fill="#5f5060")

    candidates = _build_text_region_candidates(
        image,
        [{"box": [52, 40, 232, 76], "text": "Welcome back", "score": 0.92, "source": "ocr"}],
    )

    assert candidates
    assert candidates[0].label == "heading-text"
    assert "basligi" in _component_display_name(candidates[0], 420, 220)


def test_container_candidates_are_pruned_when_specific_children_exist():
    container = ComponentCandidate(
        x=20,
        y=20,
        width=260,
        height=160,
        label="content-group",
        confidence=0.7,
        contrast_ratio=4.5,
        dominant_dark="#333333",
        dominant_light="#ffffff",
        severity="low",
        description="container",
        pixel_density=0.3,
        cluster_size=3,
    )
    button = ComponentCandidate(
        x=160,
        y=120,
        width=90,
        height=34,
        label="action-button",
        confidence=0.9,
        contrast_ratio=3.8,
        dominant_dark="#6c44db",
        dominant_light="#ffffff",
        severity="medium",
        description="button",
        pixel_density=0.35,
        cluster_size=1,
        text_hint="SIGN IN",
        text_region_count=1,
    )
    helper = ComponentCandidate(
        x=152,
        y=78,
        width=100,
        height=20,
        label="small-text",
        confidence=0.82,
        contrast_ratio=5.0,
        dominant_dark="#888888",
        dominant_light="#ffffff",
        severity="low",
        description="helper",
        pixel_density=0.22,
        cluster_size=1,
        text_hint="Email",
        text_region_count=1,
    )

    pruned = _prune_container_candidates([container, button, helper])

    assert container not in pruned
    assert button in pruned
    assert helper in pruned


def test_dino_candidates_can_attach_text_hint_to_button_role():
    image = Image.new("RGB", (320, 180), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((60, 72, 240, 120), radius=12, fill="#6c44db")
    draw.text((118, 88), "SIGN IN", fill="#ffffff")

    candidates = _build_dino_candidates(
        image,
        [{"label": "button", "score": 0.94, "box": [56, 68, 244, 124]}],
        [{"box": [102, 82, 210, 108], "text": "SIGN IN", "score": 0.91, "source": "ocr"}],
    )

    assert candidates
    assert candidates[0].label == "action-button"
    assert candidates[0].text_hint == "SIGN IN"


def test_dino_candidates_can_combine_multiple_ocr_regions():
    image = Image.new("RGB", (360, 200), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 70, 280, 114), fill="#f3f4f6")
    draw.text((118, 84), "Username or", fill="#5f5060")
    draw.text((118, 96), "email", fill="#5f5060")

    candidates = _build_dino_candidates(
        image,
        [{"label": "text field", "score": 0.92, "box": [96, 66, 286, 118]}],
        [
            {"box": [116, 82, 222, 94], "text": "Username or", "score": 0.9, "source": "ocr"},
            {"box": [116, 94, 170, 108], "text": "email", "score": 0.88, "source": "ocr"},
        ],
    )

    assert candidates
    assert candidates[0].label == "input-row"
    assert "Username or email" in candidates[0].text_hint


def test_fragment_icon_candidates_are_pruned_inside_semantic_boxes():
    icon_fragment = ComponentCandidate(
        x=120,
        y=88,
        width=26,
        height=26,
        label="icon-or-badge",
        confidence=0.52,
        contrast_ratio=6.0,
        dominant_dark="#444444",
        dominant_light="#ffffff",
        severity="low",
        description="fragment",
        pixel_density=0.4,
        cluster_size=1,
    )
    button_candidate = ComponentCandidate(
        x=60,
        y=72,
        width=180,
        height=48,
        label="action-button",
        confidence=0.9,
        contrast_ratio=4.0,
        dominant_dark="#6c44db",
        dominant_light="#ffffff",
        severity="medium",
        description="button",
        pixel_density=0.35,
        cluster_size=1,
        text_hint="SIGN IN",
        text_region_count=1,
    )

    pruned = _prune_fragment_icon_candidates(
        [icon_fragment, button_candidate],
        [{"box": [100, 82, 210, 108], "text": "SIGN IN", "score": 0.91, "source": "ocr"}],
        [{"label": "button", "score": 0.94, "box": [56, 68, 244, 124]}],
    )

    assert icon_fragment not in pruned
    assert button_candidate in pruned


def test_fragment_icon_candidates_are_pruned_inside_text_candidates():
    icon_fragment = ComponentCandidate(
        x=166,
        y=64,
        width=38,
        height=18,
        label="icon-or-badge",
        confidence=0.51,
        contrast_ratio=5.9,
        dominant_dark="#444444",
        dominant_light="#ffffff",
        severity="low",
        description="fragment",
        pixel_density=0.22,
        cluster_size=1,
    )
    helper_candidate = ComponentCandidate(
        x=150,
        y=56,
        width=112,
        height=28,
        label="small-text",
        confidence=0.84,
        contrast_ratio=4.6,
        dominant_dark="#555555",
        dominant_light="#ffffff",
        severity="low",
        description="helper",
        pixel_density=0.17,
        cluster_size=1,
        text_hint="Forgot password",
        text_region_count=1,
    )

    pruned = _prune_fragment_icon_candidates(
        [icon_fragment, helper_candidate],
        [{"box": [152, 58, 258, 82], "text": "Forgot password", "score": 0.9, "source": "ocr"}],
        [],
    )

    assert icon_fragment not in pruned
    assert helper_candidate in pruned


def test_text_hints_relabel_icon_fragments_as_text():
    candidates = [
        ComponentCandidate(
            x=160,
            y=60,
            width=92,
            height=24,
            label="icon-or-badge",
            confidence=0.5,
            contrast_ratio=4.2,
            dominant_dark="#5f5060",
            dominant_light="#ffffff",
            severity="low",
            description="fragment",
            pixel_density=0.2,
            cluster_size=1,
        )
    ]

    relabeled = _apply_text_hints(
        candidates,
        [{"box": [162, 62, 248, 82], "text": "Forgot password", "score": 0.88, "source": "ocr"}],
    )

    assert relabeled[0].label == "small-text"
    assert "yardimci metni" in _component_display_name(relabeled[0], 360, 200)


def test_metadata_hints_can_relabel_generic_candidate_to_action_button():
    image = Image.new("RGB", (360, 200), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((140, 92, 290, 136), radius=12, fill="#6c44db")
    draw.text((180, 104), "Giris Yap", fill="#ffffff")

    candidates = [
        ComponentCandidate(
            x=132,
            y=86,
            width=170,
            height=58,
            label="content-block",
            confidence=0.5,
            contrast_ratio=4.0,
            dominant_dark="#6c44db",
            dominant_light="#ffffff",
            severity="medium",
            description="generic",
            pixel_density=0.3,
            cluster_size=1,
        )
    ]

    relabeled = _apply_metadata_hints(
        candidates,
        [
            {
                "element_type": "button",
                "x": 140,
                "y": 92,
                "width": 150,
                "height": 44,
                "text_content": "Giris Yap",
                "aria_label": "Giris Yap",
            }
        ],
        image,
    )

    assert relabeled[0].label == "action-button"
    assert relabeled[0].text_hint == "Giris Yap"
    assert "butonu" in _component_display_name(relabeled[0], 360, 200)


def test_metadata_hints_can_create_unmatched_input_candidate():
    image = Image.new("RGB", (360, 200), "#ffffff")

    relabeled = _apply_metadata_hints(
        [],
        [
            {
                "element_type": "input",
                "x": 120,
                "y": 70,
                "width": 160,
                "height": 36,
                "placeholder": "Username or email",
                "name": "email",
            }
        ],
        image,
    )

    assert relabeled
    assert relabeled[0].label == "input-row"
    assert relabeled[0].text_hint == "Username or email"
