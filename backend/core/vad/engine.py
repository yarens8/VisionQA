"""
Visual Anomaly Detection Engine
===================================
Orchestrates all anomaly detectors and produces a unified VAD report.

Usage:
    vad = VADEngine()
    report = await vad.analyze(screenshot_path, url="https://example.com")
    print(report.to_dict())
"""

from __future__ import annotations

import base64
import io
import time
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw

from core.vad.types import (
    AnomalySeverity,
    BBox,
    DetectedElement,
    VADReport,
    VisualAnomaly,
)
from core.vad.anomalies.overlap_detector import detect_overlaps
from core.vad.anomalies.overflow_detector import detect_overflow
from core.vad.anomalies.alignment_detector import detect_alignment_issues
from core.vad.anomalies.spacing_detector import detect_spacing_issues
from core.vad.anomalies.completeness_detector import detect_completeness_issues


class VADEngine:
    """
    Visual Anomaly Detection Engine.

    Takes a screenshot (file path or base64) + optional DOM metadata,
    runs all detectors, and returns a scored report.
    """

    def __init__(self):
        self._dinox = None

    def _get_dinox(self):
        """Lazy-load DINO-X client."""
        if self._dinox is None:
            from core.models.dinox_client import DINOXClient
            self._dinox = DINOXClient()
        return self._dinox

    async def analyze(
        self,
        screenshot_path: Optional[str] = None,
        screenshot_base64: Optional[str] = None,
        url: Optional[str] = None,
        dom_metadata: Optional[List[Dict[str, Any]]] = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> VADReport:
        """
        Run full visual anomaly detection.

        Args:
            screenshot_path: Path to a PNG screenshot file
            screenshot_base64: Base64-encoded screenshot (alternative to path)
            url: Page URL (for context)
            dom_metadata: Element metadata extracted from DOM (via WebExecutor)
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height

        Returns:
            VADReport with all detected anomalies and scores
        """
        start_time = time.perf_counter()

        # ── Step 1: Load image ──
        if screenshot_path:
            image = Image.open(screenshot_path).convert("RGB")
        elif screenshot_base64:
            raw = screenshot_base64
            if "," in raw:
                raw = raw.split(",", 1)[1]
            image_bytes = base64.b64decode(raw)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        else:
            raise ValueError("screenshot_path veya screenshot_base64 gerekli.")

        w, h = image.size
        print(f"🔍 [VAD] Analiz basliyor: {w}x{h} gorsel, URL={url or 'N/A'}")

        # ── Step 2: Detect elements with DINO-X ──
        elements: List[DetectedElement] = []

        dino_path = None
        try:
            if screenshot_path:
                dino_path = screenshot_path
            else:
                # Save to temp for DINO
                import tempfile, os
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                dino_path = tmp.name
                tmp.close()
                image.save(dino_path)

            raw_elements = await self._get_dinox().detect_elements(dino_path)
            for elem in raw_elements:
                box = elem.get("box", [])
                if isinstance(box, list) and len(box) == 4:
                    x1, y1, x2, y2 = box
                    bbox = BBox(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
                elif isinstance(box, dict):
                    bbox = BBox(
                        x=box.get("xmin", 0),
                        y=box.get("ymin", 0),
                        width=box.get("xmax", 0) - box.get("xmin", 0),
                        height=box.get("ymax", 0) - box.get("ymin", 0),
                    )
                else:
                    continue

                if bbox.area < 100:
                    continue

                elements.append(DetectedElement(
                    label=elem.get("label", "unknown"),
                    bbox=bbox,
                    confidence=elem.get("score", 0.0),
                    source="dino",
                ))
        except Exception as dino_err:
            print(f"⚠️ [VAD] DINO-X kullanilamiyor ({type(dino_err).__name__}), DOM + piksel analizi ile devam ediliyor.")
        finally:
            if dino_path and dino_path != screenshot_path:
                try:
                    os.remove(dino_path)
                except Exception:
                    pass

        # Add DOM elements if available
        if dom_metadata:
            for meta in dom_metadata:
                mw = meta.get("width", 0)
                mh = meta.get("height", 0)
                if mw <= 0 or mh <= 0:
                    continue
                elements.append(DetectedElement(
                    label=meta.get("element_type", "element"),
                    bbox=BBox(
                        x=meta.get("x", 0),
                        y=meta.get("y", 0),
                        width=mw,
                        height=mh,
                    ),
                    confidence=1.0,
                    source="dom",
                    element_type=meta.get("element_type", ""),
                    text_content=meta.get("text_content", ""),
                    extra=meta,
                ))

        print(f"🧩 [VAD] {len(elements)} element tespit edildi (DINO + DOM)")

        # ── Step 3: Run all detectors ──
        all_anomalies: List[VisualAnomaly] = []

        overlap_anomalies = detect_overlaps(elements)
        overflow_anomalies = detect_overflow(elements, viewport_width, viewport_height)
        alignment_anomalies = detect_alignment_issues(elements)
        spacing_anomalies = detect_spacing_issues(elements)
        completeness_anomalies = detect_completeness_issues(
            image, elements, dom_metadata
        )

        all_anomalies.extend(overlap_anomalies)
        all_anomalies.extend(overflow_anomalies)
        all_anomalies.extend(alignment_anomalies)
        all_anomalies.extend(spacing_anomalies)
        all_anomalies.extend(completeness_anomalies)

        # Assign sequential IDs
        for i, anomaly in enumerate(all_anomalies, 1):
            anomaly.id = i

        # Crop evidence images
        for anomaly in all_anomalies:
            if anomaly.bbox and anomaly.bbox.area > 0:
                anomaly.crop_base64 = _crop_to_base64(image, anomaly.bbox)

        print(f"⚠️ [VAD] {len(all_anomalies)} anomali tespit edildi:")
        print(f"   Overlap:       {len(overlap_anomalies)}")
        print(f"   Overflow:      {len(overflow_anomalies)}")
        print(f"   Alignment:     {len(alignment_anomalies)}")
        print(f"   Spacing:       {len(spacing_anomalies)}")
        print(f"   Completeness:  {len(completeness_anomalies)}")

        # ── Step 4: Calculate scores ──
        overlap_score = _score_from_anomalies(overlap_anomalies)
        overflow_score = _score_from_anomalies(overflow_anomalies)
        alignment_score = _score_from_anomalies(alignment_anomalies)
        spacing_score = _score_from_anomalies(spacing_anomalies)
        completeness_score = _score_from_anomalies(completeness_anomalies)

        overall_score = int(
            overlap_score * 0.25
            + overflow_score * 0.20
            + alignment_score * 0.15
            + spacing_score * 0.15
            + completeness_score * 0.25
        )

        # ── Step 5: Build summary ──
        if not all_anomalies:
            summary = (
                "Gorsel anomali taramasi tamamlandi. "
                "Cakisma, tasma, hizalama, bosluk veya kirik gorsel sorunu tespit edilmedi."
            )
        else:
            severity_counts = {s.value: 0 for s in AnomalySeverity}
            for a in all_anomalies:
                severity_counts[a.severity.value] += 1
            parts = []
            for sev in ["critical", "high", "medium", "low", "info"]:
                if severity_counts[sev] > 0:
                    parts.append(f"{severity_counts[sev]} {sev}")
            summary = (
                f"Gorsel anomali taramasi {len(all_anomalies)} sorun tespit etti: "
                f"{', '.join(parts)}. "
                f"Genel gorsel kalite skoru: {overall_score}/100."
            )

        duration_ms = (time.perf_counter() - start_time) * 1000

        report = VADReport(
            overall_score=overall_score,
            total_anomalies=len(all_anomalies),
            anomalies=all_anomalies,
            summary=summary,
            image_dimensions={"width": w, "height": h},
            element_count=len(elements),
            analysis_duration_ms=round(duration_ms, 1),
            overlap_score=overlap_score,
            overflow_score=overflow_score,
            alignment_score=alignment_score,
            spacing_score=spacing_score,
            completeness_score=completeness_score,
        )

        print(f"✅ [VAD] Analiz tamamlandi: Skor={overall_score}/100, Sure={duration_ms:.0f}ms")
        return report

    async def analyze_after_test(
        self,
        web_executor: Any,
        test_title: str = "",
    ) -> VADReport:
        """
        Convenience method: Take a screenshot from a running WebExecutor
        and analyze it. Designed to be called after test execution.
        """
        import tempfile
        import os

        screenshot_path = tempfile.mktemp(suffix=".png")
        try:
            await web_executor.screenshot(screenshot_path, full_page=False)

            # Extract DOM metadata for richer analysis
            dom_metadata = None
            try:
                dom_metadata = await web_executor.extract_accessibility_metadata()
            except Exception as e:
                print(f"⚠️ [VAD] DOM metadata alinamadi: {e}")

            viewport = {"width": 1280, "height": 720}
            if getattr(web_executor, "page", None) and web_executor.page.viewport_size:
                viewport = web_executor.page.viewport_size

            return await self.analyze(
                screenshot_path=screenshot_path,
                url=web_executor.page.url if getattr(web_executor, "page", None) else None,
                dom_metadata=dom_metadata,
                viewport_width=viewport.get("width", 1280),
                viewport_height=viewport.get("height", 720),
            )
        finally:
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_from_anomalies(anomalies: List[VisualAnomaly]) -> int:
    """Calculate a 0-100 score from a list of anomalies."""
    if not anomalies:
        return 100
    penalty = 0
    for a in anomalies:
        if a.severity == AnomalySeverity.CRITICAL:
            penalty += 30
        elif a.severity == AnomalySeverity.HIGH:
            penalty += 20
        elif a.severity == AnomalySeverity.MEDIUM:
            penalty += 12
        elif a.severity == AnomalySeverity.LOW:
            penalty += 6
        else:
            penalty += 2
    return max(0, 100 - penalty)


def _crop_to_base64(image: Image.Image, bbox: BBox, padding: int = 10) -> str:
    """Crop a region from the image and return as base64 PNG."""
    w, h = image.size
    x1 = max(0, int(bbox.x - padding))
    y1 = max(0, int(bbox.y - padding))
    x2 = min(w, int(bbox.x2 + padding))
    y2 = min(h, int(bbox.y2 + padding))

    if x2 <= x1 or y2 <= y1:
        return ""

    cropped = image.crop((x1, y1, x2, y2))
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")
