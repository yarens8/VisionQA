"""
Visual Anomaly Detection — Core Types
========================================
Data structures for VAD findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AnomalyType(str, Enum):
    """Categories of visual anomalies."""

    OVERLAP = "overlap"
    OVERFLOW = "overflow"
    BROKEN_IMAGE = "broken_image"
    ALIGNMENT = "alignment"
    EMPTY_AREA = "empty_area"
    SPACING = "spacing"
    RESPONSIVE = "responsive"


class AnomalySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class BBox:
    """Bounding box in pixel coordinates."""

    x: float
    y: float
    width: float
    height: float

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height

    @property
    def area(self) -> float:
        return max(0, self.width) * max(0, self.height)

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    def intersection_area(self, other: "BBox") -> float:
        """Calculate intersection area with another bbox."""
        ix1 = max(self.x, other.x)
        iy1 = max(self.y, other.y)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        return (ix2 - ix1) * (iy2 - iy1)

    def iou(self, other: "BBox") -> float:
        """Intersection over Union."""
        inter = self.intersection_area(other)
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0

    def overlap_ratio(self, other: "BBox") -> float:
        """What fraction of the SMALLER box is covered by the overlap."""
        inter = self.intersection_area(other)
        smaller = min(self.area, other.area)
        return inter / smaller if smaller > 0 else 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class DetectedElement:
    """A UI element detected on screen (from DINO or DOM)."""

    label: str
    bbox: BBox
    confidence: float = 0.0
    source: str = "dino"  # "dino" or "dom"
    element_type: str = ""
    text_content: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualAnomaly:
    """A single detected visual anomaly."""

    id: int
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    title: str
    description: str
    recommendation: str
    bbox: Optional[BBox] = None
    related_elements: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    crop_base64: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "related_elements": self.related_elements,
            "evidence": self.evidence,
        }
        if self.bbox:
            result["bounding_box"] = self.bbox.to_dict()
        if self.crop_base64:
            result["crop_image_base64"] = self.crop_base64
        return result


@dataclass
class VADReport:
    """Complete VAD analysis report."""

    overall_score: int = 100
    total_anomalies: int = 0
    anomalies: List[VisualAnomaly] = field(default_factory=list)
    summary: str = ""
    image_dimensions: Dict[str, int] = field(default_factory=dict)
    element_count: int = 0
    analysis_duration_ms: float = 0.0

    # Score breakdown
    overlap_score: int = 100
    overflow_score: int = 100
    alignment_score: int = 100
    spacing_score: int = 100
    completeness_score: int = 100  # broken images, empty areas

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "total_anomalies": self.total_anomalies,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "summary": self.summary,
            "image_dimensions": self.image_dimensions,
            "element_count": self.element_count,
            "analysis_duration_ms": self.analysis_duration_ms,
            "scores": {
                "overlap": self.overlap_score,
                "overflow": self.overflow_score,
                "alignment": self.alignment_score,
                "spacing": self.spacing_score,
                "completeness": self.completeness_score,
            },
        }
