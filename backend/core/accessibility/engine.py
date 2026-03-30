"""
VisionQA Accessibility Engine
Visual-first accessibility analysis based on screenshot pixels.
"""

from __future__ import annotations

import base64
import asyncio
import io
import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageStat


@dataclass
class TileAnalysis:
    x: int
    y: int
    width: int
    height: int
    contrast_ratio: float
    color_distance: float
    dominant_dark: str
    dominant_light: str
    severity: str
    description: str


@dataclass
class ComponentCandidate:
    x: int
    y: int
    width: int
    height: int
    label: str
    confidence: float
    contrast_ratio: float
    dominant_dark: str
    dominant_light: str
    severity: str
    description: str
    pixel_density: float = 0.0
    cluster_size: int = 1
    text_hint: str = ""
    text_region_count: int = 0


SEVERITY_COLORS = {
    "high": (239, 68, 68, 36),
    "medium": (245, 158, 11, 28),
    "low": (59, 130, 246, 24),
    "pass": (16, 185, 129, 10),
}

DEFAULT_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def _normalize_base64_image(image_data: str) -> bytes:
    if "," in image_data and image_data.strip().startswith("data:"):
        _, image_data = image_data.split(",", 1)
    return base64.b64decode(image_data)


def _resolve_tesseract_command() -> Optional[str]:
    env_path = os.environ.get("TESSERACT_CMD", "").strip()
    if env_path and os.path.exists(env_path):
        return env_path

    discovered = shutil.which("tesseract")
    if discovered:
        return discovered

    for candidate in DEFAULT_TESSERACT_PATHS:
        if os.path.exists(candidate):
            return candidate

    return None


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _srgb_channel_to_linear(channel: float) -> float:
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    r, g, b = rgb
    return (
        0.2126 * _srgb_channel_to_linear(r)
        + 0.7152 * _srgb_channel_to_linear(g)
        + 0.0722 * _srgb_channel_to_linear(b)
    )


def contrast_ratio(color_a: Tuple[int, int, int], color_b: Tuple[int, int, int]) -> float:
    lum_a = relative_luminance(color_a)
    lum_b = relative_luminance(color_b)
    lighter = max(lum_a, lum_b)
    darker = min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def color_distance(color_a: Tuple[int, int, int], color_b: Tuple[int, int, int]) -> float:
    return sum((a - b) ** 2 for a, b in zip(color_a, color_b)) ** 0.5


def _image_to_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _crop_to_base64(image: Image.Image, x: int, y: int, width: int, height: int, padding: int = 16) -> str:
    safe_width = max(1, int(width))
    safe_height = max(1, int(height))

    raw_left = min(int(x), int(x) + safe_width)
    raw_top = min(int(y), int(y) + safe_height)
    raw_right = max(int(x), int(x) + safe_width)
    raw_bottom = max(int(y), int(y) + safe_height)

    max_left = max(0, image.width - 1)
    max_top = max(0, image.height - 1)

    left = max(0, min(max_left, raw_left - padding))
    top = max(0, min(max_top, raw_top - padding))
    right = max(0, min(image.width, raw_right + padding))
    bottom = max(0, min(image.height, raw_bottom + padding))

    if right <= left:
        left = max(0, min(max_left, raw_left))
        right = min(image.width, max(left + 1, min(image.width, raw_right + 1)))

    if bottom <= top:
        top = max(0, min(max_top, raw_top))
        bottom = min(image.height, max(top + 1, min(image.height, raw_bottom + 1)))

    return _image_to_base64(image.crop((left, top, right, bottom)))


def _quantized_extremes(tile: Image.Image) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    palette_image = tile.convert("P", palette=Image.Palette.ADAPTIVE, colors=6).convert("RGB")
    colors = palette_image.getcolors(maxcolors=tile.width * tile.height) or []
    if not colors:
        stat = ImageStat.Stat(tile.convert("RGB"))
        mean_rgb = tuple(int(channel) for channel in stat.mean[:3])
        return mean_rgb, mean_rgb

    unique = [rgb for _, rgb in colors]
    darkest = min(unique, key=relative_luminance)
    lightest = max(unique, key=relative_luminance)
    return darkest, lightest


def _severity_for_ratio(ratio: float) -> str:
    if ratio < 3:
        return "high"
    if ratio < 4.5:
        return "medium"
    if ratio < 7:
        return "low"
    return "pass"


def _description_for_ratio(ratio: float, distance: float) -> str:
    if ratio < 3:
        return "Gorsel ayrismasi zayif. Bu alandaki metin veya kontroller ayirt edilmesi zor bir gorunum veriyor."
    if ratio < 4.5:
        return "Normal metin icin WCAG AA seviyesinin altinda. Bu alan bircok kullanici icin zor okunabilir."
    if distance < 40:
        return "Renkler birbirine fazla yakin. Bu durum bilesen sinirlarini belirsizlestirebilir."
    return "Bu alanin kontrast seviyesi temel kullanim senaryolari icin kabul edilebilir."


def _palette_summary(image: Image.Image) -> List[Dict]:
    reduced = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=6).convert("RGB")
    colors = reduced.getcolors(maxcolors=image.width * image.height) or []
    total = sum(count for count, _ in colors) or 1
    top_colors = sorted(colors, reverse=True)[:5]
    return [
        {
            "color": _rgb_to_hex(rgb),
            "coverage": round((count / total) * 100, 1),
        }
        for count, rgb in top_colors
    ]


def _background_reference(image: Image.Image) -> Tuple[int, int, int]:
    colors = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=4).convert("RGB")
    palette = colors.getcolors(maxcolors=image.width * image.height) or []
    if not palette:
        stat = ImageStat.Stat(image)
        return tuple(int(channel) for channel in stat.mean[:3])
    return max(palette, key=lambda item: item[0])[1]


def _classify_component(
    x: int,
    y: int,
    width: int,
    height: int,
    ratio: float,
    distance: float,
    pixel_density: float,
    cluster_size: int,
    image_width: int,
    image_height: int,
) -> Tuple[str, float]:
    aspect_ratio = width / max(height, 1)
    center_x = x + width / 2
    center_y = y + height / 2
    top_band = center_y < image_height * 0.28
    right_side = center_x > image_width * 0.58
    area_ratio = (width * height) / max(image_width * image_height, 1)

    if cluster_size >= 2 and area_ratio > 0.015:
        if right_side and top_band:
            return "form-panel", 0.88
    if cluster_size >= 3 and area_ratio > 0.03:
        if top_band:
            return "hero-panel", 0.8
        return "content-group", 0.74
    if right_side and y < image_height * 0.45 and area_ratio > 0.06 and height > 70:
        return "form-panel", 0.82
    if aspect_ratio > 2.8 and height >= 30:
        if pixel_density > 0.42:
            return "action-button", 0.78
        return "input-row", 0.74
    if width < 48 and height < 48:
        return "icon-or-badge", 0.52
    if aspect_ratio > 4.5 and height < 28:
        return "text-line", 0.61
    if height < 24:
        return "small-text", 0.58
    if distance < 35:
        return "low-separation-block", 0.55
    return "content-block", 0.5


def _build_candidate(
    image: Image.Image,
    x: int,
    y: int,
    width: int,
    height: int,
    foreground_pixels: int,
    cluster_size: int = 1,
) -> ComponentCandidate:
    image_width, image_height = image.size
    bounded_width = min(image_width - x, max(1, width))
    bounded_height = min(image_height - y, max(1, height))
    crop = image.crop((x, y, min(image_width, x + bounded_width), min(image_height, y + bounded_height)))
    darkest, lightest = _quantized_extremes(crop)
    ratio = round(contrast_ratio(darkest, lightest), 2)
    distance = round(color_distance(darkest, lightest), 2)
    severity = _severity_for_ratio(ratio)
    description = _description_for_ratio(ratio, distance)
    pixel_density = round(foreground_pixels / max(bounded_width * bounded_height, 1), 3)
    label, confidence = _classify_component(
        x=x,
        y=y,
        width=bounded_width,
        height=bounded_height,
        ratio=ratio,
        distance=distance,
        pixel_density=pixel_density,
        cluster_size=cluster_size,
        image_width=image_width,
        image_height=image_height,
    )
    return ComponentCandidate(
        x=x,
        y=y,
        width=bounded_width,
        height=bounded_height,
        label=label,
        confidence=confidence,
        contrast_ratio=ratio,
        dominant_dark=_rgb_to_hex(darkest),
        dominant_light=_rgb_to_hex(lightest),
        severity=severity,
        description=description,
        pixel_density=pixel_density,
        cluster_size=cluster_size,
        text_hint="",
        text_region_count=0,
    )


def _component_priority(candidate: ComponentCandidate, image_width: int, image_height: int) -> float:
    area_ratio = (candidate.width * candidate.height) / max(image_width * image_height, 1)
    center_x = candidate.x + candidate.width / 2
    center_y = candidate.y + candidate.height / 2

    score = 0.0

    if candidate.severity == "high":
        score += 4.0
    elif candidate.severity == "medium":
        score += 2.5
    elif candidate.severity == "low":
        score += 1.0

    score += min(area_ratio * 220, 3.0)
    score += candidate.confidence * 1.4

    if candidate.label in {"action-button", "input-row", "text-line", "heading-text", "form-panel"}:
        score += 1.4
    if candidate.label in {"small-text", "icon-or-badge"}:
        score -= 1.4
    if candidate.label in {"form-panel", "content-group"}:
        score += 1.1
    if candidate.text_hint:
        score += 2.2
    if candidate.text_region_count and candidate.label in {"action-button", "input-row", "text-line", "small-text"}:
        score += 1.0
    if candidate.label in {"content-block", "content-group", "hero-panel"} and candidate.text_region_count >= 2 and not candidate.text_hint:
        score -= 2.4
    score += min(candidate.cluster_size * 0.45, 1.5)

    if center_y < image_height * 0.68:
        score += 0.8
    if center_y > image_height * 0.75:
        score -= 1.6
    if candidate.height < 28 and candidate.width < 80:
        score -= 1.1
    if area_ratio < 0.0025:
        score -= 1.4

    if center_x > image_width * 0.6 and center_y < image_height * 0.45:
        score += 0.9

    return score


def _component_display_name(candidate: ComponentCandidate, image_width: int, image_height: int) -> str:
    text_hint = _truncate_text_hint(candidate.text_hint)
    if text_hint:
        if candidate.label == "action-button":
            return f'"{text_hint}" butonu'
        if candidate.label == "input-row":
            return f'"{text_hint}" giris alani'
        if candidate.label == "text-line":
            return f'"{text_hint}" metni'
        if candidate.label == "heading-text":
            return f'"{text_hint}" basligi'
        if candidate.label == "small-text":
            return f'"{text_hint}" yardimci metni'

    center_x = candidate.x + candidate.width / 2
    center_y = candidate.y + candidate.height / 2
    top_band = center_y < image_height * 0.22
    right_side = center_x > image_width * 0.62
    left_side = center_x < image_width * 0.34
    middle_band = image_height * 0.22 <= center_y <= image_height * 0.68
    lower_band = center_y > image_height * 0.72

    if candidate.label == "form-panel":
        return "giris veya form paneli"
    if candidate.label == "hero-panel":
        return "ust kahraman alani"
    if candidate.label == "content-group":
        if right_side and top_band:
            return "giris paneli"
        if top_band:
            return "ust icerik grubu"
        return "gruplu icerik alani"
    if candidate.label == "action-button":
        if right_side and top_band:
            return "birincil aksiyon butonu"
        if lower_band:
            return "alt aksiyon butonu"
        return "aksiyon butonu"
    if candidate.label == "input-row":
        if right_side and top_band:
            return "giris formu alani"
        if right_side and middle_band:
            return "sag taraftaki form kontroli"
        if left_side and middle_band:
            return "sol taraftaki etkilesimli alan"
        if lower_band:
            return "navigasyon aksiyon satiri"
        return "etkilesimli alan"
    if candidate.label == "text-line":
        if top_band:
            return "ust baslik metni"
        if middle_band:
            return "govde metni"
        return "destekleyici metin"
    if candidate.label == "heading-text":
        if top_band:
            return "ust baslik metni"
        return "baslik metni"
    if candidate.label == "small-text":
        return "kucuk yardimci metin"
    if candidate.label == "icon-or-badge":
        return "ikon bileseni"
    if candidate.label == "subtle-form-row":
        return "dusuk belirginlikli form satiri"
    if candidate.label == "low-separation-block":
        return "dusuk ayrismali icerik alani"
    if top_band:
        return "hero icerik alani"
    if lower_band:
        return "alt icerik alani"
    if right_side:
        return "sag taraftaki icerik blogu"
    if left_side:
        return "sol taraftaki icerik blogu"
    return "icerik blogu"


def _component_title(candidate: ComponentCandidate, image_width: int, image_height: int) -> str:
    name = _component_display_name(candidate, image_width, image_height)
    if candidate.severity == "high":
        return f"{name} icin kritik kontrast sorunu"
    if candidate.severity == "medium":
        return f"{name} icin zayif kontrast sorunu"
    return f"{name} kontrast acisindan gozden gecirilmeli"


def _component_description(candidate: ComponentCandidate, image_width: int, image_height: int) -> str:
    name = _component_display_name(candidate, image_width, image_height)
    if candidate.contrast_ratio < 3:
        return f"Tespit edilen {name}, arka planla fazla karisiyor ve ayirt edilmesi zor gorunuyor."
    if candidate.contrast_ratio < 4.5:
        return f"Tespit edilen {name}, normal metin veya kontroller icin WCAG AA seviyesinin altinda oldugu icin okumayi zorlastirabilir."
    return f"Tespit edilen {name}, minimum guvenli kontrast sinirina yakin oldugu icin gozden gecirilmelidir."


def _component_recommendation(candidate: ComponentCandidate, image_width: int, image_height: int) -> str:
    name = _component_display_name(candidate, image_width, image_height)
    return (
        f"{name} icin {candidate.dominant_dark} ve {candidate.dominant_light} arasindaki ayrismayi artir. "
        "Daha koyu bir on plan ya da daha acik bir zemin tercih et."
    )


def _touch_target_threshold(platform: str) -> int:
    if platform == "mobile":
        return 48
    return 44


def _interactive_touch_target_candidates(candidates: List[ComponentCandidate]) -> List[ComponentCandidate]:
    interactive_labels = {"action-button", "input-row", "icon-or-badge"}
    return [candidate for candidate in candidates if candidate.label in interactive_labels]


def _touch_target_severity(width: int, height: int, threshold: int) -> str:
    smallest_edge = min(width, height)
    if smallest_edge < threshold - 12:
        return "high"
    if smallest_edge < threshold - 4:
        return "medium"
    return "low"


def _touch_target_description(candidate: ComponentCandidate, threshold: int, image_width: int, image_height: int) -> str:
    name = _component_display_name(candidate, image_width, image_height)
    return (
        f"Tespit edilen {name} dokunma/hedef boyutu acisindan kucuk gorunuyor. "
        f"Bu alan yaklasik {candidate.width}x{candidate.height}px ve onerilen minimum {threshold}x{threshold}px esiginin altinda."
    )


def _touch_target_recommendation(candidate: ComponentCandidate, threshold: int, image_width: int, image_height: int) -> str:
    name = _component_display_name(candidate, image_width, image_height)
    return (
        f"{name} icin tiklanabilir alan boyutunu en az {threshold}x{threshold}px seviyesine yaklastir. "
        "Icerik ayni kalsa bile padding veya buton kapsama alanini buyut."
    )


def _touch_target_findings(
    candidates: List[ComponentCandidate],
    image: Image.Image,
    image_width: int,
    image_height: int,
    platform: str,
    start_id: int,
) -> List[Dict]:
    threshold = _touch_target_threshold(platform)
    findings: List[Dict] = []

    for candidate in _interactive_touch_target_candidates(candidates):
        if candidate.width >= threshold and candidate.height >= threshold:
            continue

        findings.append(
            {
                "id": start_id + len(findings),
                "title": f"{_component_display_name(candidate, image_width, image_height)} icin dokunma alani sorunu",
                "severity": _touch_target_severity(candidate.width, candidate.height, threshold),
                "category": "touch-target",
                "description": _touch_target_description(candidate, threshold, image_width, image_height),
                "wcag_status": "touch-target-fail",
                "contrast_ratio": candidate.contrast_ratio,
                "dominant_dark": candidate.dominant_dark,
                "dominant_light": candidate.dominant_light,
                "bounding_box": {
                    "x": candidate.x,
                    "y": candidate.y,
                    "width": candidate.width,
                    "height": candidate.height,
                },
                "crop_image_base64": _crop_to_base64(image, candidate.x, candidate.y, candidate.width, candidate.height),
                "recommendation": _touch_target_recommendation(candidate, threshold, image_width, image_height),
            }
        )

        if len(findings) >= 3:
            break

    return findings


def _focus_visibility_candidates(candidates: List[ComponentCandidate]) -> List[ComponentCandidate]:
    return [candidate for candidate in candidates if candidate.label in {"action-button", "input-row", "icon-or-badge", "form-panel"}]


def _focus_visibility_findings(
    candidates: List[ComponentCandidate],
    image: Image.Image,
    image_width: int,
    image_height: int,
    start_id: int,
) -> List[Dict]:
    findings: List[Dict] = []

    for candidate in _focus_visibility_candidates(candidates):
        if candidate.contrast_ratio >= 3.2:
            continue
        if candidate.pixel_density > 0.42 and candidate.label == "action-button":
            continue

        severity = "high" if candidate.contrast_ratio < 2.2 else "medium"
        name = _component_display_name(candidate, image_width, image_height)
        findings.append(
            {
                "id": start_id + len(findings),
                "title": f"{name} icin odak gorunurlugu riski",
                "severity": severity,
                "category": "focus-visibility",
                "description": (
                    f"Tespit edilen {name} odak/outline sinyali acisindan zayif gorunuyor. "
                    "Klavye ile gezinmede secili durum yeterince belirgin olmayabilir."
                ),
                "wcag_status": "focus-visibility-risk",
                "contrast_ratio": candidate.contrast_ratio,
                "dominant_dark": candidate.dominant_dark,
                "dominant_light": candidate.dominant_light,
                "bounding_box": {
                    "x": candidate.x,
                    "y": candidate.y,
                    "width": candidate.width,
                    "height": candidate.height,
                },
                "crop_image_base64": _crop_to_base64(image, candidate.x, candidate.y, candidate.width, candidate.height),
                "recommendation": (
                    f"{name} icin daha belirgin focus ring, outline veya arka plan degisimi kullan. "
                    "Secili durum normal gorunumden daha net ayrissin."
                ),
            }
        )

        if len(findings) >= 3:
            break

    return findings


def _metadata_bounding_box(element: Dict) -> Dict[str, int]:
    return {
        "x": int(element.get("x") or 0),
        "y": int(element.get("y") or 0),
        "width": max(1, int(element.get("width") or 1)),
        "height": max(1, int(element.get("height") or 1)),
    }


def _metadata_crop(image: Image.Image, element: Dict) -> str:
    box = _metadata_bounding_box(element)
    return _crop_to_base64(image, box["x"], box["y"], box["width"], box["height"])


def _metadata_text_hint(element: Dict) -> str:
    candidates = [
        element.get("aria_label"),
        element.get("alt_text"),
        element.get("placeholder"),
        element.get("text_content"),
        element.get("title"),
        element.get("value"),
        element.get("name"),
    ]
    for value in candidates:
        normalized = _truncate_text_hint(str(value or "").strip(), max_len=72)
        if normalized:
            return normalized
    return ""


def _map_metadata_element_type(element: Dict) -> Optional[str]:
    element_type = str(element.get("element_type") or "").strip().lower()
    text_hint = _metadata_text_hint(element)
    width = max(1, int(element.get("width") or 1))
    height = max(1, int(element.get("height") or 1))

    if element_type in {"button"}:
        return "action-button"
    if element_type in {"input", "textarea", "select", "editable"}:
        return "input-row"
    if element_type in {"link"}:
        return "small-text" if height <= 28 or width < 140 else "text-line"
    if element_type in {"checkbox", "radio"}:
        return "icon-or-badge"
    if element_type in {"image", "img", "icon-button-image"}:
        return "icon-or-badge" if width < 96 and height < 96 else None

    if text_hint:
        return _infer_label_from_text_hint(text_hint, width, height, "content-block", 0.45)
    return None


def _metadata_confidence(label: str) -> float:
    if label == "action-button":
        return 0.95
    if label == "input-row":
        return 0.94
    if label in {"text-line", "heading-text"}:
        return 0.9
    if label == "small-text":
        return 0.86
    if label == "icon-or-badge":
        return 0.8
    return 0.78


def _truncate_text_hint(text: str, max_len: int = 28) -> str:
    normalized = " ".join((text or "").replace("\n", " ").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3].rstrip() + "..."


def _normalize_text_for_matching(text: str) -> str:
    translation_map = str.maketrans(
        {
            "\u00e7": "c",
            "\u011f": "g",
            "\u0131": "i",
            "\u00f6": "o",
            "\u015f": "s",
            "\u00fc": "u",
            "\u00c7": "c",
            "\u011e": "g",
            "\u0130": "i",
            "\u00d6": "o",
            "\u015e": "s",
            "\u00dc": "u",
        }
    )
    return " ".join((text or "").translate(translation_map).lower().split())


def _compact_normalized_text(text: str) -> str:
    return _normalize_text_for_matching(text).replace(" ", "")


def _text_hint_has_letters(text: str) -> bool:
    return any(character.isalpha() for character in (text or ""))


def _group_ocr_word_regions(word_regions: List[Dict]) -> List[Dict]:
    grouped: Dict[Tuple[int, int, int], List[Dict]] = {}
    ordered_keys: List[Tuple[int, int, int]] = []

    for region in word_regions:
        key = (
            int(region.get("block_num", 0) or 0),
            int(region.get("par_num", 0) or 0),
            int(region.get("line_num", 0) or 0),
        )
        if key not in grouped:
            grouped[key] = []
            ordered_keys.append(key)
        grouped[key].append(region)

    merged: List[Dict] = []
    for key in ordered_keys:
        regions = sorted(grouped[key], key=lambda item: (item["box"][0], item["box"][1]))
        if not regions:
            continue

        texts = [str(item.get("text", "")).strip() for item in regions if str(item.get("text", "")).strip()]
        if not texts:
            continue

        left = min(item["box"][0] for item in regions)
        top = min(item["box"][1] for item in regions)
        right = max(item["box"][2] for item in regions)
        bottom = max(item["box"][3] for item in regions)
        avg_score = round(sum(float(item.get("score", 0.0) or 0.0) for item in regions) / max(len(regions), 1), 2)

        merged.append(
            {
                "box": [left, top, right, bottom],
                "text": _truncate_text_hint(" ".join(texts), max_len=72),
                "score": avg_score,
                "source": "ocr",
                "block_num": key[0],
                "par_num": key[1],
                "line_num": key[2],
            }
        )

    return merged


def _try_extract_text_regions_with_tesseract(image: Image.Image) -> List[Dict]:
    tesseract_command = _resolve_tesseract_command()
    if not tesseract_command:
        return []

    try:
        import pytesseract
        from pytesseract import Output
    except Exception:
        return []

    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_command
        data = pytesseract.image_to_data(image, output_type=Output.DICT, config="--psm 6")
    except Exception:
        return []

    text_regions: List[Dict] = []
    total = len(data.get("text", []))
    for index in range(total):
        text = _truncate_text_hint(str(data["text"][index]).strip(), max_len=48)
        confidence_raw = str(data.get("conf", ["-1"] * total)[index]).strip()
        try:
            confidence = float(confidence_raw)
        except ValueError:
            confidence = -1.0

        width = int(data.get("width", [0] * total)[index] or 0)
        height = int(data.get("height", [0] * total)[index] or 0)
        if not text or confidence < 35 or width < 12 or height < 8:
            continue

        left = int(data.get("left", [0] * total)[index] or 0)
        top = int(data.get("top", [0] * total)[index] or 0)
        text_regions.append(
            {
                "box": [left, top, left + width, top + height],
                "text": text,
                "score": round(confidence / 100.0, 2),
                "source": "ocr",
                "block_num": int(data.get("block_num", [0] * total)[index] or 0),
                "par_num": int(data.get("par_num", [0] * total)[index] or 0),
                "line_num": int(data.get("line_num", [0] * total)[index] or 0),
            }
        )

    return _group_ocr_word_regions(text_regions)


def _detect_text_like_regions(image: Image.Image) -> List[Dict]:
    try:
        import cv2
        import numpy as np
    except Exception:
        return []

    rgb = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    threshold = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        15,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    merged = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions: List[Dict] = []
    image_width, image_height = image.size
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        area = width * height
        aspect_ratio = width / max(height, 1)

        if area < 120 or width < 20 or height < 8:
            continue
        if aspect_ratio < 1.6:
            continue
        if width > image_width * 0.96 or height > image_height * 0.22:
            continue

        regions.append(
            {
                "box": [x, y, x + width, y + height],
                "text": "",
                "score": 0.35,
                "source": "text-like",
            }
        )

    regions.sort(
        key=lambda item: (item["box"][2] - item["box"][0]) * (item["box"][3] - item["box"][1]),
        reverse=True,
    )
    return regions[:24]


def _detect_text_regions(image: Image.Image) -> List[Dict]:
    return _try_extract_text_regions_with_tesseract(image) or _detect_text_like_regions(image)


def _infer_label_from_text_hint(
    text_hint: str,
    width: int,
    height: int,
    current_label: str,
    text_coverage: float = 0.0,
) -> str:
    normalized = _normalize_text_for_matching(text_hint)
    compact = _compact_normalized_text(text_hint)
    aspect_ratio = width / max(height, 1)

    action_keywords = (
        "sign in",
        "signin",
        "sign up",
        "signup",
        "login",
        "log in",
        "continue with",
        "continue",
        "devam",
        "submit",
        "start",
        "get started",
        "next",
        "buy",
        "sepete ekle",
        "simdi al",
        "kayit ol",
        "giris yap",
        "search",
        "ara",
    )
    input_keywords = (
        "email",
        "e posta",
        "eposta",
        "password",
        "sifre",
        "telefon",
        "phone",
        "username",
        "usernameoremail",
        "username or email",
        "kullanici",
        "adres",
        "remember me",
    )
    helper_keywords = (
        "hint",
        "helper",
        "ornek",
        "example",
        "zorunlu",
        "required",
        "optional",
        "forgot",
        "password",
        "create account",
        "new here",
        "remember me",
    )

    if normalized:
        if any(keyword in normalized or keyword.replace(" ", "") in compact for keyword in action_keywords) and width >= 72 and height >= 22:
            return "action-button"
        if any(keyword in normalized or keyword.replace(" ", "") in compact for keyword in helper_keywords) and height <= 28:
            return "small-text"
        if any(keyword in normalized or keyword.replace(" ", "") in compact for keyword in input_keywords) and width >= 92:
            return "input-row"
        if _text_hint_has_letters(text_hint):
            if height >= 24 and width >= 120 and aspect_ratio >= 2.0:
                return "heading-text"
            if width >= 52 and aspect_ratio >= 1.8:
                return "text-line"

    if current_label in {"content-block", "content-group", "low-separation-block"}:
        if height <= 22:
            return "small-text"
        if height <= 48 and aspect_ratio >= 2.8:
            return "text-line"
        if height <= 72 and aspect_ratio >= 2.0 and text_coverage >= 0.16:
            return "action-button"

    if current_label == "icon-or-badge" and _text_hint_has_letters(text_hint):
        if height <= 24 or width < 110:
            return "small-text"
        return "text-line"

    return current_label


def _expand_box_for_text_role(
    image_width: int,
    image_height: int,
    box: List[int],
    inferred_label: str,
) -> List[int]:
    x1, y1, x2, y2 = box
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)

    pad_x = 0
    pad_y = 0
    if inferred_label == "action-button":
        pad_x = int(max(18, width * 0.55))
        pad_y = int(max(10, height * 0.95))
    elif inferred_label == "input-row":
        pad_x = int(max(20, width * 0.65))
        pad_y = int(max(10, height * 0.85))
    elif inferred_label == "small-text":
        pad_x = int(max(6, width * 0.15))
        pad_y = int(max(4, height * 0.2))
    elif inferred_label == "text-line":
        pad_x = int(max(10, width * 0.2))
        pad_y = int(max(5, height * 0.35))
    elif inferred_label == "heading-text":
        pad_x = int(max(12, width * 0.18))
        pad_y = int(max(6, height * 0.28))

    return [
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(image_width, x2 + pad_x),
        min(image_height, y2 + pad_y),
    ]


def _build_text_region_candidates(image: Image.Image, text_regions: List[Dict]) -> List[ComponentCandidate]:
    candidates: List[ComponentCandidate] = []
    image_width, image_height = image.size

    for region in text_regions:
        box = region.get("box") or []
        if len(box) != 4:
            continue

        x1, y1, x2, y2 = [int(value) for value in box]
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        if width < 18 or height < 8:
            continue
        if width > image_width * 0.98 or height > image_height * 0.24:
            continue

        text_hint = _truncate_text_hint(str(region.get("text") or ""), max_len=48)
        inferred_label = _infer_label_from_text_hint(
            text_hint=text_hint,
            width=width,
            height=height,
            current_label="text-line" if height <= 42 else "content-block",
            text_coverage=1.0,
        )
        expanded_box = _expand_box_for_text_role(image_width, image_height, [x1, y1, x2, y2], inferred_label)
        ex1, ey1, ex2, ey2 = expanded_box
        expanded_width = max(1, ex2 - ex1)
        expanded_height = max(1, ey2 - ey1)

        base_candidate = _build_candidate(
            image=image,
            x=ex1,
            y=ey1,
            width=expanded_width,
            height=expanded_height,
            foreground_pixels=max(1, int(expanded_width * expanded_height * 0.34)),
            cluster_size=1,
        )

        confidence = max(base_candidate.confidence, 0.78 if text_hint else 0.42)
        if inferred_label == "small-text":
            confidence = max(confidence, 0.7)
        if inferred_label == "action-button":
            confidence = max(confidence, 0.82)
        if inferred_label == "input-row":
            confidence = max(confidence, 0.8)
        if inferred_label == "heading-text":
            confidence = max(confidence, 0.76)

        candidates.append(
            ComponentCandidate(
                x=base_candidate.x,
                y=base_candidate.y,
                width=base_candidate.width,
                height=base_candidate.height,
                label=inferred_label,
                confidence=confidence,
                contrast_ratio=base_candidate.contrast_ratio,
                dominant_dark=base_candidate.dominant_dark,
                dominant_light=base_candidate.dominant_light,
                severity=base_candidate.severity,
                description=base_candidate.description,
                pixel_density=base_candidate.pixel_density,
                cluster_size=1,
                text_hint=text_hint,
                text_region_count=1,
            )
        )

    return candidates


def _box_intersection_area(candidate: ComponentCandidate, box: List[float]) -> float:
    x1, y1, x2, y2 = box
    inter_x1 = max(candidate.x, x1)
    inter_y1 = max(candidate.y, y1)
    inter_x2 = min(candidate.x + candidate.width, x2)
    inter_y2 = min(candidate.y + candidate.height, y2)
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    return inter_w * inter_h


def _apply_text_hints(candidates: List[ComponentCandidate], text_regions: List[Dict]) -> List[ComponentCandidate]:
    if not text_regions:
        return candidates

    relabeled: List[ComponentCandidate] = []
    for candidate in candidates:
        candidate_area = max(1, candidate.width * candidate.height)
        overlapping_regions: List[Dict] = []
        overlap_area = 0.0
        strongest_text = ""
        strongest_score = -1.0

        for region in text_regions:
            box = region.get("box") or []
            if len(box) != 4:
                continue
            intersection = _box_intersection_area(candidate, box)
            if intersection <= 0:
                continue

            region_area = max(1.0, (box[2] - box[0]) * (box[3] - box[1]))
            if intersection < 0.18 * region_area and intersection < 0.08 * candidate_area:
                continue

            overlapping_regions.append(region)
            overlap_area += intersection

            text = _truncate_text_hint(str(region.get("text") or ""), max_len=48)
            score = float(region.get("score") or 0.0)
            if text and score >= strongest_score:
                strongest_text = text
                strongest_score = score

        if not overlapping_regions:
            relabeled.append(candidate)
            continue

        text_coverage = overlap_area / candidate_area
        aspect_ratio = candidate.width / max(candidate.height, 1)
        new_label = candidate.label

        if candidate.label == "icon-or-badge" and strongest_text and _text_hint_has_letters(strongest_text):
            if candidate.height <= 24 or candidate.width < 110:
                new_label = "small-text"
            else:
                new_label = "text-line"
        elif candidate.label == "icon-or-badge" and text_coverage >= 0.2 and candidate.width >= 36:
            new_label = "small-text"

        new_label = _infer_label_from_text_hint(
            text_hint=strongest_text,
            width=candidate.width,
            height=candidate.height,
            current_label=new_label,
            text_coverage=text_coverage,
        )

        relabeled.append(
            ComponentCandidate(
                x=candidate.x,
                y=candidate.y,
                width=candidate.width,
                height=candidate.height,
                label=new_label,
                confidence=max(candidate.confidence, 0.66 if strongest_text else candidate.confidence),
                contrast_ratio=candidate.contrast_ratio,
                dominant_dark=candidate.dominant_dark,
                dominant_light=candidate.dominant_light,
                severity=candidate.severity,
                description=candidate.description,
                pixel_density=candidate.pixel_density,
                cluster_size=candidate.cluster_size,
                text_hint=strongest_text or candidate.text_hint,
                text_region_count=len(overlapping_regions),
            )
        )

    return relabeled


def _is_container_label(label: str) -> bool:
    return label in {"content-block", "content-group", "hero-panel", "form-panel", "low-separation-block"}


def _is_specific_label(label: str) -> bool:
    return label in {"action-button", "input-row", "text-line", "heading-text", "small-text", "icon-or-badge"}


def _prune_container_candidates(candidates: List[ComponentCandidate]) -> List[ComponentCandidate]:
    if not candidates:
        return candidates

    pruned: List[ComponentCandidate] = []
    for candidate in candidates:
        if not _is_container_label(candidate.label):
            pruned.append(candidate)
            continue

        specific_children = 0
        total_specific_overlap = 0.0
        candidate_area = max(1, candidate.width * candidate.height)

        for other in candidates:
            if other is candidate or not _is_specific_label(other.label):
                continue

            overlap = _box_intersection_area(candidate, [other.x, other.y, other.x + other.width, other.y + other.height])
            if overlap <= 0:
                continue

            other_area = max(1, other.width * other.height)
            if overlap < 0.55 * other_area:
                continue

            specific_children += 1
            total_specific_overlap += overlap

        if specific_children >= 2 or total_specific_overlap >= candidate_area * 0.22:
            continue

        pruned.append(candidate)

    return pruned


def _metadata_overlap(candidate: ComponentCandidate, element: Dict) -> float:
    box = _metadata_bounding_box(element)
    element_candidate = ComponentCandidate(
        x=box["x"],
        y=box["y"],
        width=box["width"],
        height=box["height"],
        label="content-block",
        confidence=0.0,
        contrast_ratio=0.0,
        dominant_dark="#000000",
        dominant_light="#ffffff",
        severity="low",
        description="",
    )
    return _intersection_ratio(candidate, element_candidate)


def _apply_metadata_hints(
    candidates: List[ComponentCandidate],
    element_metadata: List[Dict],
    image: Image.Image,
) -> List[ComponentCandidate]:
    if not element_metadata:
        return candidates

    updated: List[ComponentCandidate] = []
    matched_metadata: Set[int] = set()

    for candidate in candidates:
        best_match: Optional[Dict] = None
        best_overlap = 0.0

        for index, element in enumerate(element_metadata):
            overlap = _metadata_overlap(candidate, element)
            if overlap < 0.42:
                continue
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = {"index": index, "element": element}

        if not best_match:
            updated.append(candidate)
            continue

        matched_metadata.add(best_match["index"])
        element = best_match["element"]
        metadata_label = _map_metadata_element_type(element) or candidate.label
        metadata_text = _metadata_text_hint(element)
        box = _metadata_bounding_box(element)

        best_x = box["x"]
        best_y = box["y"]
        best_width = box["width"]
        best_height = box["height"]

        if candidate.label in {"form-panel", "hero-panel", "content-group"} and metadata_label in {"action-button", "input-row", "text-line", "heading-text", "small-text"}:
            best_x = candidate.x
            best_y = candidate.y
            best_width = candidate.width
            best_height = candidate.height

        updated.append(
            ComponentCandidate(
                x=best_x,
                y=best_y,
                width=best_width,
                height=best_height,
                label=metadata_label,
                confidence=max(candidate.confidence, _metadata_confidence(metadata_label)),
                contrast_ratio=candidate.contrast_ratio,
                dominant_dark=candidate.dominant_dark,
                dominant_light=candidate.dominant_light,
                severity=candidate.severity,
                description=candidate.description,
                pixel_density=candidate.pixel_density,
                cluster_size=max(candidate.cluster_size, 1),
                text_hint=metadata_text or candidate.text_hint,
                text_region_count=max(candidate.text_region_count, 1 if metadata_text else candidate.text_region_count),
            )
        )

    for index, element in enumerate(element_metadata):
        if index in matched_metadata:
            continue

        metadata_label = _map_metadata_element_type(element)
        if not metadata_label:
            continue

        box = _metadata_bounding_box(element)
        base_candidate = _build_candidate(
            image=image,
            x=box["x"],
            y=box["y"],
            width=box["width"],
            height=box["height"],
            foreground_pixels=max(1, int(box["width"] * box["height"] * 0.34)),
            cluster_size=1,
        )
        metadata_text = _metadata_text_hint(element)

        updated.append(
            ComponentCandidate(
                x=base_candidate.x,
                y=base_candidate.y,
                width=base_candidate.width,
                height=base_candidate.height,
                label=metadata_label,
                confidence=max(base_candidate.confidence, _metadata_confidence(metadata_label)),
                contrast_ratio=base_candidate.contrast_ratio,
                dominant_dark=base_candidate.dominant_dark,
                dominant_light=base_candidate.dominant_light,
                severity=base_candidate.severity,
                description=base_candidate.description,
                pixel_density=base_candidate.pixel_density,
                cluster_size=1,
                text_hint=metadata_text,
                text_region_count=1 if metadata_text else 0,
            )
        )

    return updated


def _alt_text_findings(
    element_metadata: List[Dict],
    image: Image.Image,
    start_id: int,
) -> List[Dict]:
    findings: List[Dict] = []

    for element in element_metadata:
        element_type = (element.get("element_type") or "").lower()
        if element_type not in {"image", "img", "icon-button-image"}:
            continue

        alt_text = (element.get("alt_text") or "").strip()
        aria_label = (element.get("aria_label") or "").strip()
        accessible_name = alt_text or aria_label
        if accessible_name and len(accessible_name) >= 3:
            continue

        box = _metadata_bounding_box(element)
        findings.append(
            {
                "id": start_id + len(findings),
                "title": "gorsel bileseni icin alt-text eksigi",
                "severity": "high",
                "category": "alt-text",
                "description": "Bu gorsel bileseni icin anlamli bir alternatif metin bulunamadi.",
                "wcag_status": "alt-text-missing",
                "contrast_ratio": 0.0,
                "dominant_dark": "#000000",
                "dominant_light": "#ffffff",
                "bounding_box": box,
                "crop_image_base64": _metadata_crop(image, element),
                "recommendation": "Gorsel amacini anlatan kisa ve anlamli bir alt-text veya aria-label ekle.",
            }
        )

    return findings


def _keyboard_navigation_findings(
    element_metadata: List[Dict],
    image: Image.Image,
    start_id: int,
) -> List[Dict]:
    findings: List[Dict] = []

    for element in element_metadata:
        keyboard_focusable = element.get("keyboard_focusable")
        focus_visible = element.get("focus_visible")
        if keyboard_focusable is not False and focus_visible is not False:
            continue

        box = _metadata_bounding_box(element)
        issue = "klavye ile erisilemiyor" if keyboard_focusable is False else "focus gorunurlugu yok"
        recommendation = (
            "Bu bileseni klavye ile odaklanabilir hale getir ve mantikli tab sirasina ekle."
            if keyboard_focusable is False
            else "Odaklandiginda belirgin outline, ring veya stil degisimi ekle."
        )

        findings.append(
            {
                "id": start_id + len(findings),
                "title": f"etkilesimli bilesen icin klavye erisimi sorunu",
                "severity": "high" if keyboard_focusable is False else "medium",
                "category": "keyboard-navigation",
                "description": f"Bu etkilesimli bilesen {issue}.",
                "wcag_status": "keyboard-navigation-risk",
                "contrast_ratio": 0.0,
                "dominant_dark": "#000000",
                "dominant_light": "#ffffff",
                "bounding_box": box,
                "crop_image_base64": _metadata_crop(image, element),
                "recommendation": recommendation,
            }
        )

    return findings


def _intersection_ratio(a: ComponentCandidate, b: ComponentCandidate) -> float:
    intersect_x = max(0, min(a.x + a.width, b.x + b.width) - max(a.x, b.x))
    intersect_y = max(0, min(a.y + a.height, b.y + b.height) - max(a.y, b.y))
    intersection = intersect_x * intersect_y
    if intersection <= 0:
        return 0.0
    return intersection / max(1, min(a.width * a.height, b.width * b.height))


def _gap_distance(a: ComponentCandidate, b: ComponentCandidate) -> Tuple[int, int]:
    horizontal_gap = max(0, max(a.x, b.x) - min(a.x + a.width, b.x + b.width))
    vertical_gap = max(0, max(a.y, b.y) - min(a.y + a.height, b.y + b.height))
    return horizontal_gap, vertical_gap


def _should_merge(a: ComponentCandidate, b: ComponentCandidate, image_width: int, image_height: int) -> bool:
    if _intersection_ratio(a, b) > 0.2:
        return True

    horizontal_gap, vertical_gap = _gap_distance(a, b)
    max_height = max(a.height, b.height)
    max_width = max(a.width, b.width)
    a_center_y = a.y + a.height / 2
    b_center_y = b.y + b.height / 2

    if abs(a_center_y - b_center_y) > image_height * 0.18:
        return False
    if vertical_gap > image_height * 0.08:
        return False

    if vertical_gap <= max(18, int(max_height * 0.7)) and horizontal_gap <= max(28, int(max_width * 0.35)):
        return True
    if horizontal_gap <= max(18, int(max_width * 0.18)) and vertical_gap <= max(36, int(max_height * 1.4)):
        return True

    if abs(a_center_y - b_center_y) < image_height * 0.04 and horizontal_gap < image_width * 0.04:
        return True

    return False


def _merge_candidate_clusters(image: Image.Image, candidates: List[ComponentCandidate]) -> List[ComponentCandidate]:
    if not candidates:
        return []

    image_width, image_height = image.size
    groups: List[List[ComponentCandidate]] = []
    visited: Set[int] = set()

    for index, candidate in enumerate(candidates):
        if index in visited:
            continue

        stack = [index]
        visited.add(index)
        group_indices = []

        while stack:
            current = stack.pop()
            group_indices.append(current)
            for other_index, other in enumerate(candidates):
                if other_index in visited:
                    continue
                if _should_merge(candidates[current], other, image_width, image_height):
                    visited.add(other_index)
                    stack.append(other_index)

        groups.append([candidates[group_index] for group_index in group_indices])

    merged: List[ComponentCandidate] = []
    for group in groups:
        if len(group) < 2:
            continue
        left = min(item.x for item in group)
        top = min(item.y for item in group)
        right = max(item.x + item.width for item in group)
        bottom = max(item.y + item.height for item in group)
        foreground_pixels = sum(max(1, int(item.pixel_density * item.width * item.height)) for item in group)
        merged.append(
            _build_candidate(
                image=image,
                x=left,
                y=top,
                width=right - left,
                height=bottom - top,
                foreground_pixels=foreground_pixels,
                cluster_size=len(group),
            )
        )

    return merged


def _detect_component_candidates(image: Image.Image, text_regions: Optional[List[Dict]] = None) -> List[ComponentCandidate]:
    width, height = image.size
    scale = min(1.0, 320 / max(width, height))
    small_width = max(1, int(width * scale))
    small_height = max(1, int(height * scale))
    small = image.resize((small_width, small_height)).convert("RGB")

    background = _background_reference(small)
    threshold = 28

    visited: Set[Tuple[int, int]] = set()
    candidates: List[ComponentCandidate] = []
    pixels = small.load()

    def is_foreground(px: int, py: int) -> bool:
        rgb = pixels[px, py]
        return color_distance(rgb, background) > threshold

    for y in range(small_height):
        for x in range(small_width):
            if (x, y) in visited or not is_foreground(x, y):
                continue

            stack = [(x, y)]
            visited.add((x, y))
            min_x = max_x = x
            min_y = max_y = y
            area = 0

            while stack:
                cx, cy = stack.pop()
                area += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)

                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < small_width and 0 <= ny < small_height and (nx, ny) not in visited and is_foreground(nx, ny):
                        visited.add((nx, ny))
                        stack.append((nx, ny))

            box_width = max_x - min_x + 1
            box_height = max_y - min_y + 1
            if area < 18 or box_width < 6 or box_height < 4:
                continue

            original_x = int(min_x / scale)
            original_y = int(min_y / scale)
            original_w = max(1, int(box_width / scale))
            original_h = max(1, int(box_height / scale))

            candidates.append(
                _build_candidate(
                    image=image,
                    x=original_x,
                    y=original_y,
                    width=original_w,
                    height=original_h,
                    foreground_pixels=max(1, int(area / max(scale * scale, 0.0001))),
                )
            )

    candidates.extend(_merge_candidate_clusters(image, candidates))
    if text_regions:
        candidates.extend(_build_text_region_candidates(image, text_regions))

    original_candidates = list(candidates)
    filtered_candidates: List[ComponentCandidate] = []
    for candidate in candidates:
        area_ratio = (candidate.width * candidate.height) / max(width * height, 1)
        center_y = candidate.y + candidate.height / 2

        # Ignore very small footer/icon regions unless they are genuinely large enough to matter.
        if area_ratio < 0.0018 and center_y > height * 0.68:
            continue
        if candidate.label == "icon-or-badge" and area_ratio < 0.004:
            # Touch-target analizi icin kucuk ikonlari tamamen kaybetme.
            if candidate.width >= _touch_target_threshold("web") and candidate.height >= _touch_target_threshold("web"):
                continue
        if candidate.label == "small-text" and area_ratio < 0.0022:
            continue
        if candidate.label == "content-block" and candidate.cluster_size == 1 and area_ratio < 0.01:
            continue

        filtered_candidates.append(candidate)

    candidates = filtered_candidates or original_candidates
    candidates = _prune_container_candidates(candidates)
    candidates.sort(key=lambda item: _component_priority(item, width, height), reverse=True)

    deduped: List[ComponentCandidate] = []
    for candidate in candidates:
        overlaps_existing = False
        for existing in deduped:
            intersect_x = max(0, min(candidate.x + candidate.width, existing.x + existing.width) - max(candidate.x, existing.x))
            intersect_y = max(0, min(candidate.y + candidate.height, existing.y + existing.height) - max(candidate.y, existing.y))
            intersection = intersect_x * intersect_y
            candidate_area = candidate.width * candidate.height
            existing_area = existing.width * existing.height
            if intersection > 0.6 * min(candidate_area, existing_area):
                overlaps_existing = True
                break
        if not overlaps_existing:
            deduped.append(candidate)
        if len(deduped) >= 12:
            break

    return deduped


def _component_summary(candidates: List[ComponentCandidate], image_width: int, image_height: int) -> List[Dict]:
    return [
        {
            "id": index,
            "label": _component_display_name(candidate, image_width, image_height),
            "severity": candidate.severity,
            "average_contrast_ratio": candidate.contrast_ratio,
            "bounding_box": {
                "x": candidate.x,
                "y": candidate.y,
                "width": candidate.width,
                "height": candidate.height,
            },
        }
        for index, candidate in enumerate(candidates[:8], start=1)
    ]


def _box_iou(candidate: ComponentCandidate, box: List[float]) -> float:
    x1, y1, x2, y2 = box
    candidate_x2 = candidate.x + candidate.width
    candidate_y2 = candidate.y + candidate.height

    inter_x1 = max(candidate.x, x1)
    inter_y1 = max(candidate.y, y1)
    inter_x2 = min(candidate_x2, x2)
    inter_y2 = min(candidate_y2, y2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    intersection = inter_w * inter_h
    if intersection <= 0:
        return 0.0

    candidate_area = candidate.width * candidate.height
    detected_area = max(1.0, (x2 - x1) * (y2 - y1))
    union = candidate_area + detected_area - intersection
    return intersection / max(union, 1.0)


def _box_overlap_ratio(box_a: List[float], box_b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    intersection = inter_w * inter_h
    if intersection <= 0:
        return 0.0

    area_a = max(1.0, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1.0, (bx2 - bx1) * (by2 - by1))
    return intersection / max(1.0, min(area_a, area_b))


def _map_dino_label(label: str) -> Optional[str]:
    normalized = (label or "").strip().lower()
    mapping = {
        "button": "action-button",
        "input field": "input-row",
        "text field": "input-row",
        "search bar": "input-row",
        "icon": "icon-or-badge",
        "logo": "icon-or-badge",
        "image": "content-block",
        "form": "form-panel",
        "header": "hero-panel",
        "navigation menu": "content-group",
    }
    return mapping.get(normalized)


def _apply_detected_labels(candidates: List[ComponentCandidate], detected_elements: List[Dict]) -> List[ComponentCandidate]:
    if not detected_elements:
        return candidates

    relabeled: List[ComponentCandidate] = []
    for candidate in candidates:
        best_label = None
        best_iou = 0.0
        best_score = 0.0

        for element in detected_elements:
            mapped_label = _map_dino_label(element.get("label", ""))
            if not mapped_label:
                continue
            box = element.get("box") or []
            if len(box) != 4:
                continue
            iou = _box_iou(candidate, box)
            if iou > best_iou and iou >= 0.2:
                best_iou = iou
                best_label = mapped_label
                best_score = float(element.get("score") or 0.0)

        if not best_label:
            relabeled.append(candidate)
            continue

        # Do not let a generic/icon DINO guess downgrade a stronger text-bearing role.
        if (
            best_label == "icon-or-badge"
            and candidate.text_hint
            and _text_hint_has_letters(candidate.text_hint)
            and candidate.label in {"action-button", "input-row", "text-line", "heading-text", "small-text"}
        ):
            relabeled.append(candidate)
            continue

        relabeled.append(
            ComponentCandidate(
                x=candidate.x,
                y=candidate.y,
                width=candidate.width,
                height=candidate.height,
                label=best_label,
                confidence=max(candidate.confidence, best_score),
                contrast_ratio=candidate.contrast_ratio,
                dominant_dark=candidate.dominant_dark,
                dominant_light=candidate.dominant_light,
                severity=candidate.severity,
                description=candidate.description,
                pixel_density=candidate.pixel_density,
                cluster_size=candidate.cluster_size,
                text_hint=candidate.text_hint,
                text_region_count=candidate.text_region_count,
            )
        )

    return relabeled


def _combined_text_for_box(text_regions: List[Dict], box: List[int]) -> Tuple[str, int]:
    matched_regions: List[Dict] = []

    for region in text_regions:
        region_box = region.get("box") or []
        if len(region_box) != 4:
            continue
        overlap = _box_overlap_ratio([float(v) for v in box], [float(v) for v in region_box])
        if overlap < 0.18:
            continue
        matched_regions.append(region)

    if not matched_regions:
        return "", 0

    matched_regions.sort(
        key=lambda item: (
            int((item.get("box") or [0, 0, 0, 0])[1]),
            int((item.get("box") or [0, 0, 0, 0])[0]),
        )
    )

    texts: List[str] = []
    for region in matched_regions:
        text = _truncate_text_hint(str(region.get("text") or ""), max_len=48)
        if not text:
            continue
        if texts and _normalize_text_for_matching(texts[-1]) == _normalize_text_for_matching(text):
            continue
        texts.append(text)

    return _truncate_text_hint(" ".join(texts), max_len=72), len(matched_regions)


def _build_dino_candidates(image: Image.Image, detected_elements: List[Dict], text_regions: List[Dict]) -> List[ComponentCandidate]:
    dino_candidates: List[ComponentCandidate] = []
    image_width, image_height = image.size

    for element in detected_elements:
        mapped_label = _map_dino_label(element.get("label", ""))
        if not mapped_label:
            continue

        box = element.get("box") or []
        if len(box) != 4:
            continue

        x1, y1, x2, y2 = [int(round(value)) for value in box]
        x1 = max(0, min(image_width - 1, x1))
        y1 = max(0, min(image_height - 1, y1))
        x2 = max(x1 + 1, min(image_width, x2))
        y2 = max(y1 + 1, min(image_height, y2))

        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        if width < 16 or height < 10:
            continue

        text_hint, text_region_count = _combined_text_for_box(text_regions, [x1, y1, x2, y2])
        inferred_label = _infer_label_from_text_hint(
            text_hint=text_hint,
            width=width,
            height=height,
            current_label=mapped_label,
            text_coverage=0.45 if text_region_count else 0.0,
        )

        base_candidate = _build_candidate(
            image=image,
            x=x1,
            y=y1,
            width=width,
            height=height,
            foreground_pixels=max(1, int(width * height * 0.36)),
            cluster_size=max(1, text_region_count),
        )

        dino_candidates.append(
            ComponentCandidate(
                x=base_candidate.x,
                y=base_candidate.y,
                width=base_candidate.width,
                height=base_candidate.height,
                label=inferred_label,
                confidence=max(base_candidate.confidence, float(element.get("score") or 0.0)),
                contrast_ratio=base_candidate.contrast_ratio,
                dominant_dark=base_candidate.dominant_dark,
                dominant_light=base_candidate.dominant_light,
                severity=base_candidate.severity,
                description=base_candidate.description,
                pixel_density=base_candidate.pixel_density,
                cluster_size=max(1, text_region_count),
                text_hint=text_hint,
                text_region_count=text_region_count,
            )
        )

    return dino_candidates


def _detect_elements_with_dino(image: Image.Image) -> List[Dict]:
    try:
        from core.models.dinox_client import DINOXClient
    except Exception:
        return []

    temp_path = None
    try:
        temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_path = temp.name
        temp.close()
        image.save(temp_path, format="PNG")

        client = DINOXClient()
        try:
            elements = asyncio.run(client.detect_elements(temp_path))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                elements = loop.run_until_complete(client.detect_elements(temp_path))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        return elements or []
    except Exception:
        return []
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _prune_fragment_icon_candidates(
    candidates: List[ComponentCandidate],
    text_regions: List[Dict],
    detected_elements: List[Dict],
) -> List[ComponentCandidate]:
    if not candidates:
        return candidates

    semantic_boxes: List[List[float]] = []
    for region in text_regions:
        box = region.get("box") or []
        if len(box) == 4:
            semantic_boxes.append([float(value) for value in box])

    for element in detected_elements:
        mapped = _map_dino_label(element.get("label", ""))
        box = element.get("box") or []
        if mapped in {"action-button", "input-row", "form-panel", "hero-panel", "content-group"} and len(box) == 4:
            semantic_boxes.append([float(value) for value in box])

    for candidate in candidates:
        if candidate.label in {"action-button", "input-row", "text-line", "heading-text", "small-text", "form-panel"}:
            semantic_boxes.append(
                [
                    float(candidate.x),
                    float(candidate.y),
                    float(candidate.x + candidate.width),
                    float(candidate.y + candidate.height),
                ]
            )

    pruned: List[ComponentCandidate] = []
    for candidate in candidates:
        if candidate.label != "icon-or-badge" or candidate.text_hint:
            pruned.append(candidate)
            continue

        candidate_box = [
            float(candidate.x),
            float(candidate.y),
            float(candidate.x + candidate.width),
            float(candidate.y + candidate.height),
        ]
        should_drop = False
        for semantic_box in semantic_boxes:
            overlap = _box_overlap_ratio(candidate_box, semantic_box)
            if overlap >= 0.55:
                should_drop = True
                break

        if should_drop:
            continue

        pruned.append(candidate)

    return pruned


def _generate_overlay(
    image: Image.Image,
    tiles: List[TileAnalysis],
    findings: List[Dict],
    candidates: List[ComponentCandidate],
) -> str:
    overlay = image.convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")

    for tile in tiles:
        fill = SEVERITY_COLORS.get(tile.severity, SEVERITY_COLORS["pass"])
        box = (tile.x, tile.y, tile.x + tile.width, tile.y + tile.height)
        draw.rectangle(box, fill=fill, outline=fill[:3] + (90,), width=1)

    for finding in findings[:5]:
        box = finding["bounding_box"]
        region = (
            box["x"],
            box["y"],
            box["x"] + box["width"],
            box["y"] + box["height"],
        )
        draw.rectangle(region, outline=(255, 255, 255, 230), width=2)

    for candidate in candidates[:8]:
        draw.rectangle(
            (
                candidate.x,
                candidate.y,
                candidate.x + candidate.width,
                candidate.y + candidate.height,
            ),
            outline=(129, 140, 248, 160),
            width=2,
        )

    return _image_to_base64(overlay)


class AccessibilityEngine:
    """Screenshot-based accessibility analyzer."""

    def analyze_image(
        self,
        image_base64: str,
        platform: str = "web",
        min_tile_size: int = 96,
        element_metadata: Optional[List[Dict]] = None,
    ) -> Dict:
        image_bytes = _normalize_base64_image(image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = image.size
        element_metadata = element_metadata or []

        grid_x = max(2, min(8, width // min_tile_size or 2))
        grid_y = max(2, min(8, height // min_tile_size or 2))
        tile_width = max(1, width // grid_x)
        tile_height = max(1, height // grid_y)

        tiles: List[TileAnalysis] = []
        passing_tiles = 0

        for row in range(grid_y):
            for col in range(grid_x):
                left = col * tile_width
                upper = row * tile_height
                right = width if col == grid_x - 1 else (col + 1) * tile_width
                lower = height if row == grid_y - 1 else (row + 1) * tile_height

                tile = image.crop((left, upper, right, lower))
                darkest, lightest = _quantized_extremes(tile)
                ratio = contrast_ratio(darkest, lightest)
                distance = color_distance(darkest, lightest)
                severity = _severity_for_ratio(ratio)
                description = _description_for_ratio(ratio, distance)

                if severity == "pass":
                    passing_tiles += 1

                tiles.append(
                    TileAnalysis(
                        x=left,
                        y=upper,
                        width=right - left,
                        height=lower - upper,
                        contrast_ratio=round(ratio, 2),
                        color_distance=round(distance, 2),
                        dominant_dark=_rgb_to_hex(darkest),
                        dominant_light=_rgb_to_hex(lightest),
                        severity=severity,
                        description=description,
                    )
                )

        text_regions = _detect_text_regions(image)
        dino_elements = _detect_elements_with_dino(image)
        candidates = _detect_component_candidates(image, text_regions=text_regions)
        candidates.extend(_build_dino_candidates(image, dino_elements, text_regions))
        candidates = _apply_text_hints(candidates, text_regions)
        candidates = _apply_detected_labels(candidates, dino_elements)
        candidates = _apply_metadata_hints(candidates, element_metadata, image)
        candidates = _prune_fragment_icon_candidates(candidates, text_regions, dino_elements)

        findings = []
        meaningful_candidates = [candidate for candidate in candidates if candidate.severity != "pass"]
        for candidate in meaningful_candidates:
            if candidate.severity == "pass":
                continue

            wcag_status = "fail"
            if candidate.contrast_ratio >= 4.5:
                wcag_status = "aa-pass"
            elif candidate.contrast_ratio >= 3:
                wcag_status = "large-text-only"

            findings.append(
                {
                    "id": len(findings) + 1,
                    "title": _component_title(candidate, width, height),
                    "severity": candidate.severity,
                    "category": "component-contrast",
                    "description": _component_description(candidate, width, height),
                    "wcag_status": wcag_status,
                    "contrast_ratio": candidate.contrast_ratio,
                    "dominant_dark": candidate.dominant_dark,
                    "dominant_light": candidate.dominant_light,
                    "bounding_box": {
                        "x": candidate.x,
                        "y": candidate.y,
                        "width": candidate.width,
                        "height": candidate.height,
                    },
                    "crop_image_base64": _crop_to_base64(image, candidate.x, candidate.y, candidate.width, candidate.height),
                    "recommendation": _component_recommendation(candidate, width, height),
                }
            )
            if len(findings) >= 8:
                break

        touch_target_findings = _touch_target_findings(
            candidates=candidates,
            image=image,
            image_width=width,
            image_height=height,
            platform=platform,
            start_id=len(findings) + 1,
        )
        findings.extend(touch_target_findings)

        focus_visibility_findings = _focus_visibility_findings(
            candidates=candidates,
            image=image,
            image_width=width,
            image_height=height,
            start_id=len(findings) + 1,
        )
        findings.extend(focus_visibility_findings)

        alt_text_findings = _alt_text_findings(
            element_metadata=element_metadata,
            image=image,
            start_id=len(findings) + 1,
        )
        findings.extend(alt_text_findings)

        keyboard_navigation_findings = _keyboard_navigation_findings(
            element_metadata=element_metadata,
            image=image,
            start_id=len(findings) + 1,
        )
        findings.extend(keyboard_navigation_findings)

        if not findings:
            weak_tiles = [tile for tile in tiles if tile.severity != "pass"]
            weak_tiles.sort(key=lambda tile: tile.contrast_ratio)
            for index, tile in enumerate(weak_tiles[:4], start=1):
                wcag_status = "fail"
                if tile.contrast_ratio >= 4.5:
                    wcag_status = "aa-pass"
                elif tile.contrast_ratio >= 3:
                    wcag_status = "large-text-only"

                findings.append(
                    {
                        "id": index,
                        "title": f"gorsel bolge {index} kontrast acisindan incelenmeli",
                        "severity": tile.severity,
                        "category": "contrast",
                        "description": tile.description,
                        "wcag_status": wcag_status,
                        "contrast_ratio": tile.contrast_ratio,
                        "dominant_dark": tile.dominant_dark,
                        "dominant_light": tile.dominant_light,
                        "bounding_box": {
                            "x": tile.x,
                            "y": tile.y,
                            "width": tile.width,
                            "height": tile.height,
                        },
                        "crop_image_base64": _crop_to_base64(image, tile.x, tile.y, tile.width, tile.height),
                        "recommendation": (
                            f"{tile.dominant_dark} ve {tile.dominant_light} arasindaki ayrimi artir. "
                            "Daha net okunabilirlik icin daha koyu bir on plan veya daha acik bir arka plan kullan."
                        ),
                    }
                )

        total_tiles = len(tiles)
        score = max(0, min(100, round((passing_tiles / total_tiles) * 100)))
        wcag_summary = {
            "aaa_pass": sum(1 for tile in tiles if tile.contrast_ratio >= 7),
            "aa_pass": sum(1 for tile in tiles if tile.contrast_ratio >= 4.5),
            "large_text_only": sum(1 for tile in tiles if 3 <= tile.contrast_ratio < 4.5),
            "fail": sum(1 for tile in tiles if tile.contrast_ratio < 3),
        }

        overview = (
            "Visual-first tam sayfa kontrast analizi tamamlandi. "
            f"{wcag_summary['fail']} kritik dusuk kontrastli alan ve "
            f"{wcag_summary['large_text_only']} sinirda alan tespit edildi."
        )

        heatmap = [
            {
                "x": tile.x,
                "y": tile.y,
                "width": tile.width,
                "height": tile.height,
                "severity": tile.severity,
                "contrast_ratio": tile.contrast_ratio,
            }
            for tile in tiles
        ]

        palette = _palette_summary(image)
        color_consistency_score = 100 - min(60, max(0, (len(palette) - 3) * 12 + wcag_summary["fail"] * 6))
        components = _component_summary(meaningful_candidates or candidates, width, height)
        overlay_base64 = _generate_overlay(image, tiles, findings, candidates)

        recommendations = [
            "Isaretlenen alanlarda on plan ve arka plan ayrimini guclendir.",
            "Form ipuclari ve ikincil etiketlerde acik zemin uzerinde griye yakin metin kullanmaktan kacin.",
            "Aksiyon butonlarini ve satir ici yardimci metinleri WCAG AA kontrast hedefine gore yeniden kontrol et.",
            "Birincil aksiyonlar, ikincil aksiyonlar ve yardimci metinler gorsel olarak daha net ayrissin diye palet tutarliligini gozden gecir.",
        ]
        if touch_target_findings:
            recommendations.append(
                f"Kucuk tiklanabilir alanlari en az {_touch_target_threshold(platform)}x{_touch_target_threshold(platform)}px seviyesine yaklastir."
            )
        if focus_visibility_findings:
            recommendations.append("Odaklanan bilesenlerin secili durumunu daha belirgin hale getir.")
        if alt_text_findings:
            recommendations.append("Gorseller icin anlamli alt-text veya aria-label ekle.")
        if keyboard_navigation_findings:
            recommendations.append("Etkilesimli bilesenleri klavye ile erisilebilir ve gorunur focus durumuna sahip hale getir.")

        return {
            "platform": platform,
            "image": {"width": width, "height": height},
            "overall_score": score,
            "overview": overview,
            "wcag_summary": wcag_summary,
            "color_consistency_score": color_consistency_score,
            "palette": palette,
            "components": components,
            "findings": findings,
            "heatmap": heatmap,
            "artifacts": {
                "overlay_image_base64": overlay_base64,
                "source_image_base64": image_base64.split(",", 1)[1] if image_base64.strip().startswith("data:") and "," in image_base64 else image_base64,
            },
            "recommendations": recommendations,
        }
