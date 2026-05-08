"""
Overlap Detector
==================
Detects UI elements that visually overlap each other.

Two buttons on top of each other, a dropdown covering content,
text bleeding into another text block — these are all overlap anomalies.
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


# Minimum overlap ratio to consider it a real overlap (not just touching edges)
_OVERLAP_THRESHOLD = 0.15

# Labels that are expected to overlap (e.g., icons inside buttons)
_ALLOWED_OVERLAP_PAIRS = {
    frozenset({"icon", "button"}),
    frozenset({"icon", "navigation menu"}),
    frozenset({"logo", "navigation menu"}),
    frozenset({"logo", "header"}),
    frozenset({"icon", "link"}),
    frozenset({"input field", "icon"}),
}


def detect_overlaps(elements: List[DetectedElement]) -> List[VisualAnomaly]:
    """
    Check all element pairs for significant visual overlap.

    Returns a list of overlap anomalies sorted by severity.
    """
    if len(elements) < 2:
        return []

    anomalies: List[VisualAnomaly] = []
    seen_pairs: set = set()

    for i, elem_a in enumerate(elements):
        for j, elem_b in enumerate(elements):
            if j <= i:
                continue

            # Skip already-reported pairs
            pair_key = (i, j)
            if pair_key in seen_pairs:
                continue

            # Skip known valid overlaps (icon inside button etc.)
            label_pair = frozenset({elem_a.label.lower(), elem_b.label.lower()})
            if label_pair in _ALLOWED_OVERLAP_PAIRS:
                continue

            # Calculate overlap
            overlap_ratio = elem_a.bbox.overlap_ratio(elem_b.bbox)
            if overlap_ratio < _OVERLAP_THRESHOLD:
                continue

            seen_pairs.add(pair_key)

            # Determine severity based on overlap ratio
            if overlap_ratio > 0.6:
                severity = AnomalySeverity.HIGH
            elif overlap_ratio > 0.35:
                severity = AnomalySeverity.MEDIUM
            else:
                severity = AnomalySeverity.LOW

            # Build bounding box that covers both elements
            combined_x = min(elem_a.bbox.x, elem_b.bbox.x)
            combined_y = min(elem_a.bbox.y, elem_b.bbox.y)
            combined_x2 = max(elem_a.bbox.x2, elem_b.bbox.x2)
            combined_y2 = max(elem_a.bbox.y2, elem_b.bbox.y2)

            anomalies.append(VisualAnomaly(
                id=0,
                anomaly_type=AnomalyType.OVERLAP,
                severity=severity,
                title=f"'{elem_a.label}' ve '{elem_b.label}' elementleri ust uste biniyor",
                description=(
                    f"'{elem_a.label}' ile '{elem_b.label}' elementleri arasinda "
                    f"%{int(overlap_ratio * 100)} oraninda gorsel cakisma tespit edildi. "
                    f"Bu durum icerik okunabilirligini ve tiklanabilirligini bozabilir."
                ),
                recommendation=(
                    "Cakisan elementlerin konumlarini (margin, padding, position) duzelt "
                    "veya z-index siralamalarini kontrol et."
                ),
                bbox=BBox(
                    x=combined_x,
                    y=combined_y,
                    width=combined_x2 - combined_x,
                    height=combined_y2 - combined_y,
                ),
                related_elements=[elem_a.label, elem_b.label],
                evidence={
                    "overlap_ratio": round(overlap_ratio, 3),
                    "element_a": {"label": elem_a.label, "bbox": elem_a.bbox.to_dict()},
                    "element_b": {"label": elem_b.label, "bbox": elem_b.bbox.to_dict()},
                },
            ))

    anomalies.sort(key=lambda a: a.severity.value)
    return anomalies
