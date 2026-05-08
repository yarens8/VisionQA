"""
Completeness Detector
========================
Detects broken images, empty content areas, and missing visual elements.

Uses pixel analysis on the screenshot to find:
- Large uniform-color rectangles (possible broken image placeholders)
- Suspiciously empty areas in the layout
"""

from __future__ import annotations

from typing import List, Tuple

from PIL import Image
import numpy as np

from core.vad.types import (
    AnomalySeverity,
    AnomalyType,
    BBox,
    DetectedElement,
    VisualAnomaly,
)

# Minimum area (as fraction of viewport) to consider "suspiciously empty"
_MIN_EMPTY_AREA_RATIO = 0.04
# Minimum size for a broken image placeholder
_MIN_PLACEHOLDER_SIZE = 60


def detect_completeness_issues(
    image: Image.Image,
    elements: List[DetectedElement],
    dom_metadata: List[dict] | None = None,
) -> List[VisualAnomaly]:
    """
    Analyze the screenshot for broken images and empty areas.
    """
    anomalies: List[VisualAnomaly] = []

    # 1. Broken image detection via DOM metadata
    if dom_metadata:
        _detect_broken_images_from_dom(dom_metadata, anomalies)

    # 2. Large uniform-color blocks (possible placeholders or broken areas)
    _detect_uniform_blocks(image, elements, anomalies)

    # 3. Large empty (no-element) gaps in the layout
    _detect_empty_gaps(image, elements, anomalies)

    return anomalies


def _detect_broken_images_from_dom(
    dom_metadata: List[dict],
    anomalies: List[VisualAnomaly],
) -> None:
    """Check DOM metadata for images with missing alt or zero dimensions."""
    for meta in dom_metadata:
        if meta.get("element_type") != "image":
            continue

        w = meta.get("width", 0)
        h = meta.get("height", 0)
        alt = meta.get("alt_text", "")

        if w <= 1 or h <= 1:
            anomalies.append(VisualAnomaly(
                id=0,
                anomaly_type=AnomalyType.BROKEN_IMAGE,
                severity=AnomalySeverity.HIGH,
                title="Kirik veya yuklenmeyen gorsel tespit edildi",
                description=(
                    f"Bir <img> elementinin boyutu {w}x{h}px — "
                    "bu genellikle yuklenmeyen veya hatali bir gorsele isaret eder."
                ),
                recommendation="Gorselin src yolunu kontrol et ve fallback/placeholder ekle.",
                bbox=BBox(
                    x=meta.get("x", 0),
                    y=meta.get("y", 0),
                    width=max(w, 20),
                    height=max(h, 20),
                ),
                related_elements=["image"],
                evidence={"dimensions": f"{w}x{h}", "alt_text": alt},
            ))


def _detect_uniform_blocks(
    image: Image.Image,
    elements: List[DetectedElement],
    anomalies: List[VisualAnomaly],
) -> None:
    """
    Scan for large rectangular blocks of near-uniform color.
    These could be broken image placeholders, empty containers, etc.
    """
    w, h = image.size
    img_array = np.array(image)

    # Scan at a coarse grid
    block_size = 80
    found_regions: List[BBox] = []
    max_findings = 3

    for row_start in range(0, h - block_size, block_size):
        for col_start in range(0, w - block_size, block_size):
            if len(found_regions) >= max_findings:
                break

            block = img_array[
                row_start : row_start + block_size,
                col_start : col_start + block_size,
            ]
            std = block.std()
            if std > 8:
                continue

            full_bbox = _expand_uniform_region(
                img_array, row_start, col_start, block_size, std_threshold=12
            )
            if full_bbox is None:
                continue

            bx, by, bw, bh = full_bbox
            area_ratio = (bw * bh) / (w * h)

            if area_ratio < _MIN_EMPTY_AREA_RATIO:
                continue
            if bw < _MIN_PLACEHOLDER_SIZE or bh < _MIN_PLACEHOLDER_SIZE:
                continue

            region_bbox = BBox(x=bx, y=by, width=bw, height=bh)

            # Skip if this region significantly overlaps an already-found region
            is_duplicate = any(
                region_bbox.overlap_ratio(existing) > 0.4
                for existing in found_regions
            )
            if is_duplicate:
                continue

            found_regions.append(region_bbox)

            anomalies.append(VisualAnomaly(
                id=0,
                anomaly_type=AnomalyType.BROKEN_IMAGE,
                severity=AnomalySeverity.MEDIUM,
                title="Olasi kirik gorsel veya bos placeholder alani",
                description=(
                    f"{bw}x{bh}px boyutunda tamamen tek renkli bir alan tespit edildi. "
                    f"Bu, yuklenmeyen bir gorsel veya bos bir container olabilir."
                ),
                recommendation="Bu alandaki gorsel kaynagin dogru yuklendigini kontrol et.",
                bbox=region_bbox,
                related_elements=["placeholder"],
                evidence={
                    "area_px": f"{bw}x{bh}",
                    "area_ratio": round(area_ratio, 4),
                    "color_std": round(float(std), 2),
                },
            ))

        if len(found_regions) >= max_findings:
            break


def _expand_uniform_region(
    img_array: "np.ndarray",
    start_row: int,
    start_col: int,
    initial_size: int,
    std_threshold: float,
) -> Tuple[int, int, int, int] | None:
    """Expand a uniform block to find its full extent."""
    h, w = img_array.shape[:2]
    ref_color = img_array[
        start_row : start_row + initial_size,
        start_col : start_col + initial_size,
    ].mean(axis=(0, 1))

    # Expand right
    end_col = start_col + initial_size
    while end_col < w:
        stripe = img_array[start_row : start_row + initial_size, end_col : end_col + 10]
        if stripe.size == 0 or abs(stripe.mean() - ref_color.mean()) > std_threshold:
            break
        end_col += 10

    # Expand down
    end_row = start_row + initial_size
    while end_row < h:
        stripe = img_array[end_row : end_row + 10, start_col : end_col]
        if stripe.size == 0 or abs(stripe.mean() - ref_color.mean()) > std_threshold:
            break
        end_row += 10

    bw = end_col - start_col
    bh = end_row - start_row
    if bw < _MIN_PLACEHOLDER_SIZE or bh < _MIN_PLACEHOLDER_SIZE:
        return None
    return (start_col, start_row, bw, bh)


def _detect_empty_gaps(
    image: Image.Image,
    elements: List[DetectedElement],
    anomalies: List[VisualAnomaly],
) -> None:
    """
    Find large vertical gaps between elements where no content exists.
    """
    if len(elements) < 2:
        return

    w, h = image.size

    # Sort elements by vertical position
    sorted_elems = sorted(elements, key=lambda e: e.bbox.y)

    for i in range(len(sorted_elems) - 1):
        top_elem = sorted_elems[i]
        bottom_elem = sorted_elems[i + 1]

        gap = bottom_elem.bbox.y - top_elem.bbox.y2
        gap_ratio = gap / h if h > 0 else 0

        # Only flag very large gaps (>15% of viewport height)
        if gap_ratio < 0.15:
            continue

        anomalies.append(VisualAnomaly(
            id=0,
            anomaly_type=AnomalyType.EMPTY_AREA,
            severity=AnomalySeverity.LOW,
            title="Elementler arasinda buyuk bos alan var",
            description=(
                f"'{top_elem.label}' ile '{bottom_elem.label}' arasinda "
                f"{int(gap)}px ({int(gap_ratio * 100)}% viewport yuksekligi) "
                f"boyutunda icerik olmayan alan tespit edildi."
            ),
            recommendation=(
                "Bu bos alan kasitli degilse, elementler arasindaki "
                "margin/padding degerlerini veya eksik icerigi kontrol et."
            ),
            bbox=BBox(x=0, y=top_elem.bbox.y2, width=w, height=gap),
            related_elements=[top_elem.label, bottom_elem.label],
            evidence={
                "gap_px": int(gap),
                "gap_ratio": round(gap_ratio, 3),
                "above_element": top_elem.label,
                "below_element": bottom_elem.label,
            },
        ))
