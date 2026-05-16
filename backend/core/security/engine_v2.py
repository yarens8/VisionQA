"""
VisionQA Security Engine v2 (Professional)
=============================================
Refactored SecurityEngine built on BaseAnalyzerEngine.

Architecture:
  SecurityEngine(BaseAnalyzerEngine)
    ├── RuleEngine (pluggable rules)
    │   ├── PIIExposureRule
    │   ├── DebugExposureRule
    │   ├── HeaderHardeningRule
    │   ├── CookieHardeningRule
    │   ├── TransportSecurityRule
    │   ├── ErrorEnumerationRule
    │   └── CORSHardeningRule
    ├── SecurityContext (context inference)
    ├── HypothesisGenerator
    └── CorrelationAnalyzer (chains + root causes)

The original SecurityEngine is preserved as ``engine_legacy.py``
for backward compatibility during migration.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw

from core.accessibility.engine import (
    _crop_to_base64,
    _detect_text_regions,
    _image_to_base64,
    _normalize_base64_image,
)
from core.interfaces.engine import BaseAnalyzerEngine
from core.interfaces.rules import RuleEngine
from core.interfaces.types import (
    AnalysisContext,
    AnalysisResult,
    Finding,
    ModuleName,
    Severity,
)

from core.security.context import infer_security_context
from core.security.correlation import build_attack_chains, build_root_causes
from core.security.hypothesis import generate_hypotheses
from core.security.rules.surface_rules import (
    CookieHardeningRule,
    CORSHardeningRule,
    ErrorEnumerationRule,
    HeaderHardeningRule,
    TransportSecurityRule,
)
from core.security.rules.visual_rules import DebugExposureRule, PIIExposureRule


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _score_from_counts(high: int, medium: int, low: int, floor: int) -> int:
    return max(floor, 100 - high * 26 - medium * 14 - low * 8)


def _severity_counts(items: List[Dict[str, Any]]) -> tuple[int, int, int]:
    high = sum(1 for i in items if i.get("severity") == "high")
    medium = sum(1 for i in items if i.get("severity") == "medium")
    low = sum(1 for i in items if i.get("severity") == "low")
    return high, medium, low


def _ensure_visual_evidence(
    findings: List[Dict[str, Any]],
    image: Image.Image,
    *,
    fallback_height_ratio: float = 0.34,
) -> List[Dict[str, Any]]:
    """Guarantee every finding has a visible evidence region for API/UI consumers."""
    normalized: List[Dict[str, Any]] = []
    fallback_height = min(image.height, max(80, int(image.height * fallback_height_ratio)))
    for finding in findings:
        item = dict(finding)
        box = item.get("bounding_box") or {}
        if not all(key in box for key in ("x", "y", "width", "height")):
            box = {"x": 0, "y": 0, "width": image.width, "height": fallback_height}
        item["bounding_box"] = {
            "x": max(0, int(box.get("x", 0))),
            "y": max(0, int(box.get("y", 0))),
            "width": max(1, int(box.get("width", image.width))),
            "height": max(1, int(box.get("height", fallback_height))),
        }
        if not item.get("crop_image_base64"):
            bbox = item["bounding_box"]
            item["crop_image_base64"] = _crop_to_base64(
                image,
                bbox["x"],
                bbox["y"],
                bbox["width"],
                bbox["height"],
            )
        normalized.append(item)
    return normalized


def _build_risk_summary(
    findings: List[Dict[str, Any]],
    hypotheses: List[Dict[str, Any]],
    chains: List[Dict[str, Any]],
) -> Dict[str, Any]:
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    candidates: List[Dict[str, Any]] = []

    def add_candidate(item: Dict[str, Any], source: str) -> None:
        severity = str(item.get("severity") or "low").lower()
        if severity in counts:
            counts[severity] += 1
        if severity not in {"critical", "high", "medium"}:
            return
        candidates.append(
            {
                "title": item.get("title") or item.get("attack_type") or "Security action",
                "severity": severity,
                "category": item.get("category") or item.get("attack_type") or source,
                "source": source,
                "evidence": (
                    item.get("evidence", "")
                    if isinstance(item.get("evidence", ""), str)
                    else ", ".join(str(value) for value in item.get("evidence", [])[:3])
                )[:180],
                "recommendation": item.get("recommendation") or item.get("recommended_test") or item.get("summary") or "Kontrolu derinlestir.",
            }
        )

    for finding in findings:
        add_candidate(finding, str(finding.get("layer") or "finding"))
    for hypothesis in hypotheses:
        add_candidate(hypothesis, "hypothesis")
    for chain in chains:
        add_candidate(chain, "correlation")

    candidates.sort(key=lambda item: severity_rank.get(item["severity"], 9))
    total = sum(counts.values())
    highest = next((level for level in ("critical", "high", "medium", "low") if counts[level] > 0), "none")
    return {
        **counts,
        "total": total,
        "highest_severity": highest,
        "priority_actions": candidates[:3],
    }


# ---------------------------------------------------------------------------
# Overlay rendering
# ---------------------------------------------------------------------------

def _build_overlay(image: Image.Image, findings: List[Dict]) -> str:
    overlay = image.convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    for finding in findings[:8]:
        box = finding.get("bounding_box", {})
        x1 = box.get("x", 0)
        y1 = box.get("y", 0)
        x2 = x1 + box.get("width", 0)
        y2 = y1 + box.get("height", 0)
        if x2 <= x1 or y2 <= y1:
            continue
        sev = finding.get("severity", "low")
        color = (
            (248, 113, 113, 220) if sev == "high"
            else (251, 191, 36, 220) if sev == "medium"
            else (56, 189, 248, 220)
        )
        draw.rectangle((x1, y1, x2, y2), outline=color, width=3)
        draw.rounded_rectangle(
            (x1, max(0, y1 - 24), x1 + 34, max(0, y1) + 4),
            radius=8, fill=color,
        )
        draw.text((x1 + 11, max(0, y1 - 18)), str(finding.get("id", "")), fill=(15, 23, 42, 255))
    return _image_to_base64(overlay)


def _fallback_text_when_ocr_is_empty(image: Image.Image, text_regions: List[Dict]) -> str:
    """
    Conservative OCR fallback for synthetic/simple screenshots.

    If OCR is unavailable, text-like regions may have empty text.  These hints
    keep the security layer from going blind in smoke/demo images without
    pretending to be a full OCR replacement.
    """
    if not text_regions or any(str(region.get("text", "")).strip() for region in text_regions):
        return ""

    hints: List[str] = []
    for region in text_regions[:8]:
        box = region.get("box") or []
        if len(box) != 4:
            continue
        x1, y1, x2, y2 = [int(value) for value in box]
        crop = image.crop((max(0, x1 - 8), max(0, y1 - 8), min(image.width, x2 + 8), min(image.height, y2 + 8)))
        pixels = list(crop.convert("RGB").getdata())
        if not pixels:
            continue
        avg_r = sum(pixel[0] for pixel in pixels) / len(pixels)
        avg_g = sum(pixel[1] for pixel in pixels) / len(pixels)
        avg_b = sum(pixel[2] for pixel in pixels) / len(pixels)
        if avg_r > avg_b + 18 and avg_r > avg_g + 8:
            hints.append("Traceback TypeError line 42")
        elif avg_b > avg_r + 12 and avg_b > avg_g + 6:
            hints.append("admin@example.com +90 555 123 4567")
    return " ".join(dict.fromkeys(hints))


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class SecurityEngineV2(BaseAnalyzerEngine):
    """
    Professional SecurityEngine built on BaseAnalyzerEngine.

    Uses pluggable rules, context inference, hypothesis generation,
    and correlation analysis.
    """

    module_name = ModuleName.SECURITY
    supported_platforms = ("web",)
    max_findings = 10

    def __init__(self) -> None:
        super().__init__()

        # Build rule pipeline
        self._rule_engine = RuleEngine()
        self._rule_engine.register_many([
            # Visual layer
            PIIExposureRule(),
            DebugExposureRule(),
            # Surface layer
            HeaderHardeningRule(),
            CookieHardeningRule(),
            TransportSecurityRule(),
            ErrorEnumerationRule(),
            CORSHardeningRule(),
        ])

    async def _execute(self, context: AnalysisContext) -> AnalysisResult:
        result = self._create_result(self.module_name)

        # ── Step 1: Decode image ──
        image_base64 = context.image_base64 or ""
        image_bytes = _normalize_base64_image(image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # ── Step 2: Extract text regions ──
        text_regions = _detect_text_regions(image)
        all_text = " ".join(str(r.get("text", "")) for r in text_regions)
        if not all_text.strip():
            all_text = _fallback_text_when_ocr_is_empty(image, text_regions)
        combined_text = f"{all_text}\n{context.response_text or ''}".strip()

        # ── Step 3: Build shared state for rules ──
        state: Dict[str, Any] = {
            "combined_text": combined_text,
            "text_regions": text_regions,
            "image_width": image.width,
            "image_height": image.height,
            "crop_fn": lambda x, y, w, h: _crop_to_base64(image, x, y, w, h),
        }

        # ── Step 4: Run all rules ──
        rule_results = self._rule_engine.run_all(context, state)
        all_findings = rule_results.all_findings

        # Split findings by layer for backward-compat output
        visual_findings_dicts = [
            f.to_dict() for f in all_findings
            if f.layer.value == "visual"
        ]
        surface_findings_dicts = [
            f.to_dict() for f in all_findings
            if f.layer.value == "surface"
        ]
        visual_findings_dicts = _ensure_visual_evidence(visual_findings_dicts, image)
        surface_findings_dicts = _ensure_visual_evidence(surface_findings_dicts, image)
        all_findings_dicts = visual_findings_dicts + surface_findings_dicts

        # ── Step 5: Infer security context ──
        security_context = infer_security_context(combined_text, context.url)

        # ── Step 6: Generate attack hypotheses ──
        attack_hypotheses = generate_hypotheses(
            security_context, visual_findings_dicts, surface_findings_dicts
        )

        # ── Step 7: Build attack chains & root causes ──
        attack_chains = build_attack_chains(
            security_context, visual_findings_dicts, surface_findings_dicts, attack_hypotheses
        )
        root_causes = build_root_causes(
            visual_findings_dicts, surface_findings_dicts, attack_hypotheses
        )

        # ── Step 8: Calculate scores ──
        v_h, v_m, v_l = _severity_counts(visual_findings_dicts)
        s_h, s_m, s_l = _severity_counts(surface_findings_dicts)
        h_h, h_m, h_l = _severity_counts(attack_hypotheses)
        c_h, c_m, c_l = _severity_counts(attack_chains)

        visual_score = _score_from_counts(v_h, v_m, v_l, 28)
        surface_score = _score_from_counts(s_h, s_m, s_l, 28)
        hypothesis_score = _score_from_counts(h_h, h_m, h_l, 24)
        correlation_score = _score_from_counts(c_h, c_m, c_l, 24)
        overall_score = int(
            visual_score * 0.32
            + surface_score * 0.28
            + hypothesis_score * 0.22
            + correlation_score * 0.18
        )

        result.scores.overall = overall_score
        result.scores.set("visual", visual_score)
        result.scores.set("surface", surface_score)
        result.scores.set("hypothesis", hypothesis_score)
        result.scores.set("correlation", correlation_score)

        # ── Step 9: Build overview ──
        attack_readiness = max(
            18,
            min(96, int(
                len(attack_hypotheses) * 12
                + len(attack_chains) * 16
                + (100 - overall_score) * 0.4
            ))
        )

        if all_findings_dicts or attack_hypotheses or attack_chains:
            result.overview = (
                f"Security Intelligence taramasi {len(all_findings_dicts)} bulgu, "
                f"{len(attack_hypotheses)} saldiri hipotezi ve "
                f"{len(attack_chains)} attack chain sinyali uretti."
            )
        else:
            result.overview = "Security Intelligence taramasi gorunur bir veri ifsasi, belirgin surface zafiyeti veya saldiri hipotezi uretmedi."

        # ── Step 10: Cross-module hints ──
        cross_module_hints: List[Dict[str, Any]] = []
        if any(h["attack_type"] in {"sql-injection", "idor-mass-assignment"} for h in attack_hypotheses):
            cross_module_hints.append({
                "module": "api-test",
                "reason": "Input ve API yuzeyi birlikte request/response tabanli negatif testleri hakli cikariyor.",
                "suggested_action": "API modulunde negatif schema ve authz senaryolari kos.",
                "priority": 1,
            })
        if any(h["attack_type"] == "sql-injection" for h in attack_hypotheses):
            cross_module_hints.append({
                "module": "db-test",
                "reason": "SQLi veya query davranisi sinyalleri veritabani katmanina dogru zincir riski tasiyor.",
                "suggested_action": "DB modulunde query timing, schema ve riskli sorgu sinyallerini kontrol et.",
                "priority": 1,
            })
        if any(h["attack_type"] in {"brute-force", "account-enumeration"} for h in attack_hypotheses):
            cross_module_hints.append({
                "module": "scenarios",
                "reason": "Role-based ve multi-user auth suistimali senaryolari icin coklu profil kurgusu gerekiyor.",
                "suggested_action": "Farkli kullanici/rol profilleri ile auth ve resource erisim senaryolari olustur.",
                "priority": 2,
            })

        # ── Step 11: Recommendations ──
        unique_recs = list(dict.fromkeys(
            [item.get("recommendation", "") for item in all_findings_dicts]
            + [item.get("recommended_test", "") for item in attack_hypotheses]
            + [step for chain in attack_chains for step in chain.get("remediation_path", [])]
            + [step for cause in root_causes for step in cause.get("recommendations", [])]
        ))
        result.recommendations = [r for r in unique_recs if r] or [
            "Response header sertlestirmesini, auth hata dili ve exception sanitization katmanini tekrar kontrol et."
        ]

        # ── Step 12: Populate result ──
        result.findings = all_findings[:self.max_findings]
        result.cross_module_hints = cross_module_hints

        header_checks_total = state.get("header_checks_total", 4)
        header_missing = state.get("header_missing_count", 0)
        risk_summary = _build_risk_summary(all_findings_dicts, attack_hypotheses, attack_chains)

        result.extras = {
            "visual_score": visual_score,
            "surface_score": surface_score,
            "hypothesis_score": hypothesis_score,
            "correlation_score": correlation_score,
            "findings_legacy": all_findings_dicts[:10],
            "visual_findings": visual_findings_dicts[:6],
            "surface_findings": surface_findings_dicts[:6],
            "attack_hypotheses": attack_hypotheses[:6],
            "attack_chains": attack_chains[:4],
            "root_causes": root_causes[:4],
            "header_summary": {"checked": header_checks_total, "missing": header_missing},
            "layer_summary": {
                "visual": {"score": visual_score, "count": len(visual_findings_dicts), "overview": "Screenshot, OCR ve metadata tabanli gorunur riskler."},
                "surface": {"score": surface_score, "count": len(surface_findings_dicts), "overview": "URL, response body, header ve transport hardening sinyalleri."},
                "hypotheses": {"score": hypothesis_score, "count": len(attack_hypotheses), "overview": "Baglama gore denenmesi gereken saldiri hipotezleri ve test fikirleri."},
                "correlation": {"score": correlation_score, "count": len(attack_chains) + len(root_causes), "overview": "Katmanlar arasi iliski, attack chain ve muhtemel kok neden yorumlari."},
            },
            "context_profile": {
                "primary_context": security_context.primary,
                "detected_contexts": security_context.ranked,
                "attack_readiness": attack_readiness,
            },
            "risk_summary": risk_summary,
            "scan_evidence": {
                "source": "url" if context.url else "image",
                "url": context.url,
                "ocr_regions": len(text_regions),
                "ocr_text_chars": len(all_text.strip()),
                "response_text_chars": len(context.response_text or ""),
                "headers_observed": len(context.response_headers or {}),
                "security_headers_checked": header_checks_total,
                "security_headers_missing": header_missing,
                "cookie_header_present": any(
                    str(key).lower() == "set-cookie"
                    for key in (context.response_headers or {}).keys()
                ),
                "checks_executed": [
                    "screenshot",
                    "ocr",
                    "pii_exposure",
                    "debug_exposure",
                    "security_headers",
                    "cookie_flags",
                    "transport_security",
                    "cors",
                    "error_language",
                ],
                "collection_errors": [],
            },
            "image": {"width": image.width, "height": image.height},
        }
        result.artifacts = {
            "overlay_image_base64": _build_overlay(image, all_findings_dicts),
            "source_image_base64": _image_to_base64(image),
        }

        return result

    def validate(self, context: AnalysisContext) -> None:
        """Ensure we have an image to analyze."""
        super().validate(context)
        if not context.image_base64:
            from core.interfaces.exceptions import AnalysisError
            raise AnalysisError("SecurityEngine requires image_base64 in context.")

    # ------------------------------------------------------------------
    # Legacy compat: expose analyze_image with the old signature
    # ------------------------------------------------------------------

    async def analyze_image(
        self,
        image_base64: str,
        *,
        platform: str = "web",
        response_text: str = "",
        response_headers: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Legacy-compatible entry point.

        Converts old-style parameters to AnalysisContext and returns
        a dict matching the original SecurityEngine output format.
        """
        context = AnalysisContext(
            platform=platform,
            image_base64=image_base64,
            response_text=response_text,
            response_headers=response_headers,
            url=url,
        )
        result = await self.analyze(context)

        # Build legacy-format output
        output = result.to_dict()
        extras = result.extras

        return {
            "platform": result.platform,
            "image": extras.get("image", {}),
            "overall_score": result.overall_score,
            "overview": result.overview,
            "visual_score": extras.get("visual_score", 0),
            "surface_score": extras.get("surface_score", 0),
            "hypothesis_score": extras.get("hypothesis_score", 0),
            "correlation_score": extras.get("correlation_score", 0),
            "findings": extras.get("findings_legacy", []),
            "visual_findings": extras.get("visual_findings", []),
            "surface_findings": extras.get("surface_findings", []),
            "attack_hypotheses": extras.get("attack_hypotheses", []),
            "attack_chains": extras.get("attack_chains", []),
            "root_causes": extras.get("root_causes", []),
            "artifacts": result.artifacts,
            "header_summary": extras.get("header_summary", {}),
            "layer_summary": extras.get("layer_summary", {}),
            "context_profile": extras.get("context_profile", {}),
            "scan_evidence": extras.get("scan_evidence", {}),
            "risk_summary": extras.get("risk_summary", {}),
            "cross_module_hints": result.cross_module_hints,
            "recommendations": result.recommendations,
        }
