"""
VisionQA Core Types
====================
Standardized data structures used across ALL analysis modules.

Every engine receives an ``AnalysisContext`` and returns an ``AnalysisResult``.
Individual issues are represented as ``Finding`` objects.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from PIL import Image


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Unified severity levels across every VisionQA module."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def weight(self) -> int:
        """Numeric weight used in score calculations."""
        return {
            Severity.CRITICAL: 32,
            Severity.HIGH: 24,
            Severity.MEDIUM: 14,
            Severity.LOW: 8,
            Severity.INFO: 0,
        }[self]


class AnalysisLayer(str, Enum):
    """Which layer of the stack a finding belongs to."""

    VISUAL = "visual"
    SURFACE = "surface"
    BEHAVIORAL = "behavioral"
    STRUCTURAL = "structural"
    HYPOTHESIS = "hypothesis"
    CORRELATION = "correlation"


class ModuleName(str, Enum):
    """Registry of all analysis modules."""

    ACCESSIBILITY = "accessibility"
    SECURITY = "security"
    UIUX = "uiux"
    PERFORMANCE = "performance"
    MOBILE = "mobile"
    API_TEST = "api_test"
    DB_QUALITY = "db_quality"
    DATASET = "dataset"


# ---------------------------------------------------------------------------
# Bounding Box
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundingBox:
    """Pixel-level region on a screenshot."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


# ---------------------------------------------------------------------------
# Analysis Context  (Input to every engine)
# ---------------------------------------------------------------------------


@dataclass
class AnalysisContext:
    """
    Unified input envelope for every analysis engine.

    Engines receive this object and read only the fields they need.
    This decouples modules from each other — a Security engine does not need
    to know what fields Accessibility uses and vice versa.
    """

    # --- Core identifiers ---
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    module: Optional[ModuleName] = None
    platform: str = "web"

    # --- Visual inputs ---
    image: Optional[Image.Image] = None
    image_base64: Optional[str] = None

    # --- URL / network inputs ---
    url: Optional[str] = None
    response_text: Optional[str] = None
    response_headers: Optional[Dict[str, str]] = None

    # --- Structured metadata ---
    element_metadata: List[Dict[str, Any]] = field(default_factory=list)
    text_regions: List[Dict[str, Any]] = field(default_factory=list)

    # --- API / DB inputs ---
    api_method: Optional[str] = None
    api_url: Optional[str] = None
    api_headers: Optional[Dict[str, str]] = None
    api_body: Optional[Any] = None
    db_connection_string: Optional[str] = None
    db_query: Optional[str] = None

    # --- Config overrides ---
    config: Dict[str, Any] = field(default_factory=dict)

    # --- Timing ---
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Finding  (Individual issue / observation)
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """
    A single finding produced by an analysis engine.

    Every module emits findings in this exact shape, making them
    comparable, sortable and aggregatable across modules.
    """

    id: int
    title: str
    severity: Severity
    category: str
    description: str
    recommendation: str

    # Optional enrichment
    layer: AnalysisLayer = AnalysisLayer.VISUAL
    evidence: str = ""
    bounding_box: Optional[BoundingBox] = None
    crop_image_base64: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        return self.severity in {Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM}

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "severity": self.severity.value,
            "category": self.category,
            "layer": self.layer.value,
            "description": self.description,
            "recommendation": self.recommendation,
            "evidence": self.evidence,
        }
        if self.bounding_box:
            result["bounding_box"] = self.bounding_box.to_dict()
        if self.crop_image_base64:
            result["crop_image_base64"] = self.crop_image_base64
        if self.extra:
            result.update(self.extra)
        return result


# ---------------------------------------------------------------------------
# Score Breakdown
# ---------------------------------------------------------------------------


@dataclass
class ScoreBreakdown:
    """
    Flexible score container.

    Each engine fills in only the sub-scores it cares about.
    The ``overall`` is always present.
    """

    overall: int = 100
    sub_scores: Dict[str, int] = field(default_factory=dict)

    def deduct(self, severity: Severity, count: int = 1) -> None:
        """Apply a standard penalty based on severity."""
        self.overall = max(0, self.overall - severity.weight * count)

    def set(self, name: str, value: int) -> None:
        self.sub_scores[name] = max(0, min(100, value))

    def to_dict(self) -> Dict[str, int]:
        return {"overall": self.overall, **self.sub_scores}


# ---------------------------------------------------------------------------
# Analysis Result  (Output of every engine)
# ---------------------------------------------------------------------------


@dataclass
class AnalysisResult:
    """
    Unified output envelope returned by every analysis engine.

    Routers and consumers always receive this shape, regardless of
    which engine produced it.
    """

    # --- Identity ---
    module: ModuleName
    platform: str = "web"
    run_id: str = ""

    # --- Scores ---
    scores: ScoreBreakdown = field(default_factory=ScoreBreakdown)

    # --- Narrative ---
    overview: str = ""
    root_cause_summary: str = ""
    recommendations: List[str] = field(default_factory=list)

    # --- Findings ---
    findings: List[Finding] = field(default_factory=list)

    # --- Artifacts ---
    artifacts: Dict[str, str] = field(default_factory=dict)

    # --- Module-specific extras ---
    extras: Dict[str, Any] = field(default_factory=dict)

    # --- Timing ---
    duration_ms: float = 0.0

    # --- Cross-module hints ---
    cross_module_hints: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def overall_score(self) -> int:
        return self.scores.overall

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def high_severity_count(self) -> int:
        return sum(
            1
            for f in self.findings
            if f.severity in {Severity.CRITICAL, Severity.HIGH}
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module.value,
            "platform": self.platform,
            "run_id": self.run_id,
            "overall_score": self.overall_score,
            "scores": self.scores.to_dict(),
            "overview": self.overview,
            "root_cause_summary": self.root_cause_summary,
            "recommendations": self.recommendations,
            "findings": [f.to_dict() for f in self.findings],
            "artifacts": self.artifacts,
            "duration_ms": self.duration_ms,
            "cross_module_hints": self.cross_module_hints,
            **self.extras,
        }
