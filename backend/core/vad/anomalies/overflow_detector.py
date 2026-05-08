"""
Overflow & Clipping Detector
================================
Detects elements that extend beyond the viewport or are likely clipped/truncated.
"""

from __future__ import annotations

from typing import List

from core.vad.types import (
    AnomalySeverity,
    AnomalyType,
    BBox,
    DetectedElement,
    VisualAnomaly,
)


def detect_overflow(
    elements: List[DetectedElement],
    viewport_width: int,
    viewport_height: int,
) -> List[VisualAnomaly]:
    """
    Check elements for viewport overflow (going off-screen).
    """
    anomalies: List[VisualAnomaly] = []

    for elem in elements:
        bbox = elem.bbox
        issues: List[str] = []

        # Right edge overflow
        if bbox.x2 > viewport_width + 5:
            overflow_px = int(bbox.x2 - viewport_width)
            issues.append(f"sag kenardan {overflow_px}px tasiyor")

        # Bottom edge overflow (less critical since pages scroll)
        # We skip this for now — vertical scrolling is normal

        # Left edge negative (shouldn't happen but sometimes does)
        if bbox.x < -5:
            issues.append(f"sol kenardan {int(abs(bbox.x))}px disarida")

        # Top edge negative
        if bbox.y < -5:
            issues.append(f"ust kenardan {int(abs(bbox.y))}px disarida")

        if not issues:
            continue

        # Elements partially visible are medium, fully invisible are high
        visible_width = max(0, min(bbox.x2, viewport_width) - max(bbox.x, 0))
        visible_height = max(0, min(bbox.y2, viewport_height) - max(bbox.y, 0))
        visible_area = visible_width * visible_height
        visibility_ratio = visible_area / bbox.area if bbox.area > 0 else 0

        if visibility_ratio < 0.3:
            severity = AnomalySeverity.HIGH
        elif visibility_ratio < 0.7:
            severity = AnomalySeverity.MEDIUM
        else:
            severity = AnomalySeverity.LOW

        anomalies.append(VisualAnomaly(
            id=0,
            anomaly_type=AnomalyType.OVERFLOW,
            severity=severity,
            title=f"'{elem.label}' elementi viewport disindan tasiyor",
            description=(
                f"'{elem.label}' elementi {', '.join(issues)}. "
                f"Elementin %{int(visibility_ratio * 100)}'i gorunur durumda. "
                f"Bu durum icerige erisimi engelleyebilir."
            ),
            recommendation=(
                "Elementin CSS overflow, position ve width degerlerini kontrol et. "
                "Responsive tasarimda max-width veya media query kullan."
            ),
            bbox=bbox,
            related_elements=[elem.label],
            evidence={
                "overflow_issues": issues,
                "visibility_ratio": round(visibility_ratio, 3),
                "viewport": {"width": viewport_width, "height": viewport_height},
                "element_bbox": bbox.to_dict(),
            },
        ))

    return anomalies
