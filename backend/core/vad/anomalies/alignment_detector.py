"""
Alignment Detector
=====================
Detects elements that should be aligned but aren't.

Looks for groups of similar elements (e.g., multiple buttons, multiple inputs)
and checks if they share consistent left/right/center alignment.
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

# Pixel tolerance for alignment
_ALIGNMENT_TOLERANCE_PX = 8


def detect_alignment_issues(elements: List[DetectedElement]) -> List[VisualAnomaly]:
    """
    Group similar elements and check for alignment consistency.
    """
    if len(elements) < 3:
        return []

    anomalies: List[VisualAnomaly] = []

    # Group elements by label type
    groups: Dict[str, List[DetectedElement]] = defaultdict(list)
    for elem in elements:
        groups[elem.label.lower()].append(elem)

    for label, group in groups.items():
        if len(group) < 3:
            continue

        # Check left-edge alignment
        left_edges = [elem.bbox.x for elem in group]
        _check_alignment(
            group, left_edges, "sol kenar", label, anomalies
        )

        # Check horizontal center alignment (for things in a row)
        centers_x = [elem.bbox.center[0] for elem in group]
        _check_alignment(
            group, centers_x, "yatay merkez", label, anomalies
        )

    # Also check ALL interactive elements on same horizontal line
    _check_row_alignment(elements, anomalies)

    return anomalies


def _check_alignment(
    group: List[DetectedElement],
    values: List[float],
    axis_name: str,
    label: str,
    anomalies: List[VisualAnomaly],
) -> None:
    """Check if a group of values are consistently aligned."""
    if len(values) < 3:
        return

    # Find the most common alignment point
    sorted_vals = sorted(values)
    # Use median as the expected alignment
    median = sorted_vals[len(sorted_vals) // 2]

    outliers = []
    for i, val in enumerate(values):
        if abs(val - median) > _ALIGNMENT_TOLERANCE_PX:
            outliers.append((group[i], val, abs(val - median)))

    if not outliers or len(outliers) >= len(group) // 2:
        # If too many outliers, there's no clear alignment to break
        return

    for elem, val, deviation in outliers:
        anomalies.append(VisualAnomaly(
            id=0,
            anomaly_type=AnomalyType.ALIGNMENT,
            severity=AnomalySeverity.LOW if deviation < 15 else AnomalySeverity.MEDIUM,
            title=f"'{elem.label}' diger '{label}' elementleriyle hizali degil",
            description=(
                f"'{elem.label}' elementinin {axis_name} degeri "
                f"diger benzer elementlerden {int(deviation)}px sapma gosteriyor. "
                f"Bu gorsel tutarsizlik olusturabilir."
            ),
            recommendation=(
                f"'{label}' grubundaki tum elementlerin {axis_name} hizalamasini "
                f"kontrol et. CSS flexbox veya grid kullanarak tutarli hizalama sagla."
            ),
            bbox=elem.bbox,
            related_elements=[elem.label],
            evidence={
                "expected_position": round(median, 1),
                "actual_position": round(val, 1),
                "deviation_px": round(deviation, 1),
                "axis": axis_name,
            },
        ))


def _check_row_alignment(
    elements: List[DetectedElement],
    anomalies: List[VisualAnomaly],
) -> None:
    """Check elements on the same row for consistent vertical centering."""
    if len(elements) < 2:
        return

    # Group elements by approximate Y center (same row)
    rows: Dict[int, List[DetectedElement]] = defaultdict(list)
    for elem in elements:
        row_key = int(elem.bbox.center[1] // 30)  # 30px bucket
        rows[row_key].append(elem)

    for _row_key, row_elements in rows.items():
        if len(row_elements) < 2:
            continue

        y_centers = [elem.bbox.center[1] for elem in row_elements]
        y_median = sorted(y_centers)[len(y_centers) // 2]

        for i, elem in enumerate(row_elements):
            dev = abs(y_centers[i] - y_median)
            if dev > 12:
                anomalies.append(VisualAnomaly(
                    id=0,
                    anomaly_type=AnomalyType.ALIGNMENT,
                    severity=AnomalySeverity.LOW,
                    title=f"Ayni satirdaki '{elem.label}' dikey hizasi bozuk",
                    description=(
                        f"Ayni satirdaki elementler icinde '{elem.label}' "
                        f"dikey olarak {int(dev)}px kayik duruyor."
                    ),
                    recommendation="Ayni satirdaki elementleri vertical-align veya align-items ile hizala.",
                    bbox=elem.bbox,
                    related_elements=[elem.label],
                    evidence={"vertical_deviation_px": round(dev, 1)},
                ))
