"""
Spacing Detector
==================
Detects inconsistent spacing between similar elements.

If you have 5 product cards and the gap between them is
20, 20, 20, 45 — that 45 is a spacing anomaly.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from core.vad.types import (
    AnomalySeverity,
    AnomalyType,
    BBox,
    DetectedElement,
    VisualAnomaly,
)

# Relative tolerance — a gap must differ by this % from the median to flag
_SPACING_TOLERANCE_RATIO = 0.35
_MIN_GROUP_SIZE = 3


def detect_spacing_issues(elements: List[DetectedElement]) -> List[VisualAnomaly]:
    """
    Check groups of same-type elements for consistent spacing.
    """
    if len(elements) < _MIN_GROUP_SIZE:
        return []

    anomalies: List[VisualAnomaly] = []

    # Group by label
    groups: Dict[str, List[DetectedElement]] = defaultdict(list)
    for elem in elements:
        groups[elem.label.lower()].append(elem)

    for label, group in groups.items():
        if len(group) < _MIN_GROUP_SIZE:
            continue

        # Check vertical spacing (elements stacked)
        _check_directional_spacing(group, label, "vertical", anomalies)

        # Check horizontal spacing (elements in a row)
        _check_directional_spacing(group, label, "horizontal", anomalies)

    return anomalies


def _check_directional_spacing(
    group: List[DetectedElement],
    label: str,
    direction: str,
    anomalies: List[VisualAnomaly],
) -> None:
    """Check spacing consistency in one direction."""
    if direction == "vertical":
        sorted_elems = sorted(group, key=lambda e: e.bbox.y)
    else:
        sorted_elems = sorted(group, key=lambda e: e.bbox.x)

    if len(sorted_elems) < _MIN_GROUP_SIZE:
        return

    # Calculate gaps between consecutive elements
    gaps = []
    for i in range(len(sorted_elems) - 1):
        a = sorted_elems[i]
        b = sorted_elems[i + 1]
        if direction == "vertical":
            gap = b.bbox.y - a.bbox.y2
        else:
            gap = b.bbox.x - a.bbox.x2
        gaps.append((gap, a, b))

    if not gaps:
        return

    # Filter out negative gaps (overlapping — handled by overlap detector)
    positive_gaps = [(g, a, b) for g, a, b in gaps if g > 5]
    if len(positive_gaps) < 2:
        return

    gap_values = [g for g, _, _ in positive_gaps]
    median_gap = sorted(gap_values)[len(gap_values) // 2]

    if median_gap < 5:
        return

    for gap_val, elem_a, elem_b in positive_gaps:
        deviation = abs(gap_val - median_gap)
        if deviation <= max(5, median_gap * _SPACING_TOLERANCE_RATIO):
            continue

        combined_x = min(elem_a.bbox.x, elem_b.bbox.x)
        combined_y = min(elem_a.bbox.y, elem_b.bbox.y)
        combined_x2 = max(elem_a.bbox.x2, elem_b.bbox.x2)
        combined_y2 = max(elem_a.bbox.y2, elem_b.bbox.y2)

        severity = AnomalySeverity.LOW if deviation < 20 else AnomalySeverity.MEDIUM

        dir_label = "dikey" if direction == "vertical" else "yatay"

        anomalies.append(VisualAnomaly(
            id=0,
            anomaly_type=AnomalyType.SPACING,
            severity=severity,
            title=f"'{label}' elementleri arasinda tutarsiz {dir_label} bosluk",
            description=(
                f"'{elem_a.label}' ve '{elem_b.label}' arasindaki {dir_label} bosluk "
                f"{int(gap_val)}px, ama gruptaki normal aralik {int(median_gap)}px. "
                f"{int(deviation)}px sapma gorsel duzensizlige isaret ediyor."
            ),
            recommendation=(
                f"'{label}' grubundaki tum elementler icin tutarli "
                f"gap/margin degeri kullan. CSS gap veya consistent spacing token kullan."
            ),
            bbox=BBox(
                x=combined_x,
                y=combined_y,
                width=combined_x2 - combined_x,
                height=combined_y2 - combined_y,
            ),
            related_elements=[elem_a.label, elem_b.label],
            evidence={
                "actual_gap_px": round(gap_val, 1),
                "expected_gap_px": round(median_gap, 1),
                "deviation_px": round(deviation, 1),
                "direction": direction,
            },
        ))
