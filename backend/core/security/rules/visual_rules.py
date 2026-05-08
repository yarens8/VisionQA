"""
Visual Detection Rules — PII & Debug Exposure
================================================
Regex-based rules that scan OCR text for sensitive data leaks
and debug information exposure on screen.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.interfaces.types import AnalysisContext, AnalysisLayer, Finding, Severity
from core.interfaces.rules import Rule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _best_text_region_for_match(
    text_regions: List[Dict],
    pattern: re.Pattern[str],
) -> Optional[Dict]:
    """Find the text region that matched the pattern, for bounding-box."""
    for region in text_regions:
        if pattern.search(str(region.get("text", ""))):
            return region
    return text_regions[0] if text_regions else None


def _bbox_from_region(region: Optional[Dict], fallback_width: int, fallback_height: int) -> Dict[str, int]:
    """Extract bounding box from an OCR region, or use a fallback."""
    if region and len(region.get("box", [])) == 4:
        x1, y1, x2, y2 = [int(v) for v in region["box"]]
        return {"x": x1, "y": y1, "width": max(1, x2 - x1), "height": max(1, y2 - y1)}
    return {"x": 0, "y": 0, "width": fallback_width, "height": min(fallback_height, max(80, fallback_height // 3))}


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

_PII_PATTERNS: List[tuple[str, str, Severity, re.Pattern[str], str, str]] = [
    (
        "email-exposure",
        "Maskelenmemis e-posta bilgisi gorunuyor",
        Severity.MEDIUM,
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
        "Kullaniciya acik bir e-posta adresi ekranda gorunuyor. Bu durum gereksiz veri ifsasi yaratabilir.",
        "E-posta bilgisini maskele veya sadece gerekli baglamda goster.",
    ),
    (
        "phone-exposure",
        "Maskelenmemis telefon bilgisi gorunuyor",
        Severity.MEDIUM,
        re.compile(r"(?:(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s-]?)\d{3}[\s-]?\d{2,4}[\s-]?\d{2,4})"),
        "Telefon benzeri bir veri acik sekilde gorunuyor. Bu durum PII ifsasi riskini artirabilir.",
        "Telefon bilgisini parcali maskele veya sadece gerekli oldugunda goster.",
    ),
    (
        "token-exposure",
        "Token veya gizli anahtar benzeri veri gorunuyor",
        Severity.HIGH,
        re.compile(
            r"\b(?:bearer\s+[a-z0-9\-._~+/]+=*|sk_live_[a-z0-9]+|api[_-]?key"
            r"|secret[_-]?key|x-api-key|authorization:\s*bearer)\b",
            re.I,
        ),
        "Token veya gizli anahtar benzeri bir ifade gorunuyor. Bu durum dogrudan gizli bilgi ifsasi olabilir.",
        "Token, key ve secret degerlerini istemci yuzeyinde asla acik gostermemelisin.",
    ),
    (
        "card-exposure",
        "Kart benzeri hassas veri gorunuyor",
        Severity.HIGH,
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "Kart numarasina benzeyen bir veri gorunuyor. Bu alanin acik sekilde gosterilmesi ciddi guvenlik ve uyum riski yaratabilir.",
        "Kart numaralarini son 4 hane disinda maskele ve gorunur yuzeyden kaldir.",
    ),
]

_DEBUG_PATTERNS: List[tuple[str, str, Severity, re.Pattern[str], str, str]] = [
    (
        "stack-trace",
        "Stack trace veya exception detaylari gorunuyor",
        Severity.HIGH,
        re.compile(
            r"\b(traceback|exception|stack trace|nullreferenceexception"
            r"|typeerror|referenceerror|sqlsyntaxerror|syntax error"
            r"|stacktrace|unhandled exception|line \d+)\b",
            re.I,
        ),
        "Detayli hata izi son kullanici ekranina siziyor. Bu durum ic sistem yapisi ve kod akisi hakkinda fazla bilgi verebilir.",
        "Uretim ortaminda detayli exception ve stack trace ciktisini kullaniciya gostermeyi kapat.",
    ),
    (
        "debug-page",
        "Debug veya framework hata sayfasi sinyali var",
        Severity.MEDIUM,
        re.compile(
            r"\b(debug|developer exception page|whitelabel error page"
            r"|laravel|django|werkzeug|nextjs|express)\b",
            re.I,
        ),
        "Framework veya debug moduna ait hata ekranlari son kullaniciya gorunuyor olabilir.",
        "Debug modunu kapat ve son kullaniciya sade, guvenli hata mesaji goster.",
    ),
    (
        "config-exposure",
        "Ic konfigurasyon veya ortam bilgisi gorunuyor",
        Severity.MEDIUM,
        re.compile(
            r"\b(localhost|127\.0\.0\.1|internal|staging|production"
            r"|redis|postgres|mongodb|\.env|/var/www|c:\\\\|d:\\\\)\b",
            re.I,
        ),
        "Ortama veya servis altyapisina ait bilgi son kullanici ekranina siziyor olabilir.",
        "Environment, host, path ve servis detaylarini son kullanici ekranindan kaldir.",
    ),
]


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class PIIExposureRule(Rule):
    """Scans visible text for PII leaks (email, phone, tokens, card numbers)."""

    name = "pii-exposure"
    category = "pii"
    description = "OCR/text uzerinde PII ifsasi tespiti"

    def evaluate(self, context: AnalysisContext, state: Dict[str, Any]) -> List[Finding]:
        combined_text: str = state.get("combined_text", "")
        text_regions: List[Dict] = state.get("text_regions", [])
        image_width: int = state.get("image_width", 800)
        image_height: int = state.get("image_height", 600)
        crop_fn = state.get("crop_fn")

        findings: List[Finding] = []
        for category, title, severity, pattern, description, recommendation in _PII_PATTERNS:
            match = pattern.search(combined_text)
            if not match:
                continue

            region = _best_text_region_for_match(text_regions, pattern)
            bbox = _bbox_from_region(region, image_width, image_height)

            crop_b64 = None
            if crop_fn:
                crop_b64 = crop_fn(bbox["x"], bbox["y"], bbox["width"], bbox["height"])

            findings.append(Finding(
                id=0,
                title=title,
                severity=severity,
                category=category,
                layer=AnalysisLayer.VISUAL,
                description=description,
                recommendation=recommendation,
                evidence=match.group(0)[:180],
                extra={"bounding_box": bbox, "crop_image_base64": crop_b64 or ""},
            ))

        return findings


class DebugExposureRule(Rule):
    """Scans visible text for debug info, stack traces, config leaks."""

    name = "debug-exposure"
    category = "debug"
    description = "Screenshot/response uzerinde debug bilgi ifsasi tespiti"

    def evaluate(self, context: AnalysisContext, state: Dict[str, Any]) -> List[Finding]:
        combined_text: str = state.get("combined_text", "")
        text_regions: List[Dict] = state.get("text_regions", [])
        image_width: int = state.get("image_width", 800)
        image_height: int = state.get("image_height", 600)
        crop_fn = state.get("crop_fn")

        findings: List[Finding] = []
        for category, title, severity, pattern, description, recommendation in _DEBUG_PATTERNS:
            match = pattern.search(combined_text)
            if not match:
                continue

            region = _best_text_region_for_match(text_regions, pattern)
            bbox = _bbox_from_region(region, image_width, image_height)

            crop_b64 = None
            if crop_fn:
                crop_b64 = crop_fn(bbox["x"], bbox["y"], bbox["width"], bbox["height"])

            findings.append(Finding(
                id=0,
                title=title,
                severity=severity,
                category=category,
                layer=AnalysisLayer.VISUAL,
                description=description,
                recommendation=recommendation,
                evidence=match.group(0)[:180],
                extra={"bounding_box": bbox, "crop_image_base64": crop_b64 or ""},
            ))

        return findings
