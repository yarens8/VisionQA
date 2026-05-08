"""
VisionQA Base Analysis Engine
================================
Abstract base class that every analysis module MUST extend.

Contract
--------
1. Implement ``_execute(context) -> AnalysisResult``
2. Optionally override ``validate(context)`` for input guards
3. Optionally override ``_post_process(result)`` for enrichment

The public ``analyze()`` method orchestrates:
  validate → _execute → _post_process → timing → return
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from core.interfaces.exceptions import (
    AnalysisError,
    EngineNotReadyError,
    VisionQAException,
)
from core.interfaces.types import (
    AnalysisContext,
    AnalysisResult,
    Finding,
    ModuleName,
    ScoreBreakdown,
    Severity,
)

logger = logging.getLogger("visionqa.engine")


class BaseAnalyzerEngine(ABC):
    """
    Abstract base for every VisionQA analysis module.

    Subclasses must set ``module_name`` and implement ``_execute``.
    Everything else has sensible defaults that can be overridden.
    """

    # --- Subclass must set this ---
    module_name: ModuleName

    # --- Optional overrides ---
    supported_platforms: tuple[str, ...] = ("web",)
    max_findings: int = 20

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"visionqa.{self.module_name.value}")

    # ------------------------------------------------------------------
    # Public API — Routers call ONLY this method
    # ------------------------------------------------------------------

    async def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """
        Execute a full analysis pass.

        This is the **only** public method routers should call.
        It handles validation, timing, error containment, and post-processing.
        """
        started = time.perf_counter()
        context.module = self.module_name

        try:
            self.validate(context)
            result = await self._execute(context)
        except VisionQAException:
            raise
        except Exception as exc:
            self._logger.exception("Unhandled error in %s engine", self.module_name.value)
            raise AnalysisError(
                f"{self.module_name.value} analysis failed: {exc}",
                details=str(exc),
            ) from exc

        # Enforce limits
        result.findings = result.findings[: self.max_findings]

        # Post-process
        result = self._post_process(result)

        # Timing
        result.duration_ms = round((time.perf_counter() - started) * 1000, 2)
        result.run_id = context.run_id
        result.platform = context.platform

        return result

    # ------------------------------------------------------------------
    # Validation — Override for custom guards
    # ------------------------------------------------------------------

    def validate(self, context: AnalysisContext) -> None:
        """
        Validate that the context has everything this engine needs.

        Default implementation checks platform support.
        Override and call ``super().validate(context)`` for extra checks.
        """
        if context.platform not in self.supported_platforms:
            from core.interfaces.exceptions import UnsupportedPlatformError

            raise UnsupportedPlatformError(
                context.platform,
                details=f"{self.module_name.value} supports: {self.supported_platforms}",
            )

    # ------------------------------------------------------------------
    # Core logic — Subclass MUST implement
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute(self, context: AnalysisContext) -> AnalysisResult:
        """
        Run the actual analysis.

        Returns an ``AnalysisResult`` populated with findings, scores,
        artifacts, and narrative text.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Post-processing — Override for enrichment
    # ------------------------------------------------------------------

    def _post_process(self, result: AnalysisResult) -> AnalysisResult:
        """
        Enrich or clean the result before returning to the caller.

        Default implementation sorts findings by severity and generates
        a fallback overview if none was provided.
        """
        # Sort findings: critical/high first
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        result.findings.sort(key=lambda f: severity_order.get(f.severity, 5))

        # Fallback overview
        if not result.overview:
            result.overview = (
                f"{self.module_name.value.title()} analizi {len(result.findings)} "
                f"bulgu uretti. Genel skor: {result.overall_score}."
            )

        # Fallback recommendations from findings
        if not result.recommendations:
            result.recommendations = list(
                dict.fromkeys(
                    f.recommendation
                    for f in result.findings
                    if f.is_actionable and f.recommendation
                )
            )[:8]

        return result

    # ------------------------------------------------------------------
    # Helpers available to subclasses
    # ------------------------------------------------------------------

    @staticmethod
    def _create_result(module: ModuleName, **kwargs) -> AnalysisResult:
        """Convenience factory for creating a properly-initialized result."""
        return AnalysisResult(module=module, scores=ScoreBreakdown(), **kwargs)

    @staticmethod
    def _score_from_findings(
        findings: List[Finding],
        base: int = 100,
        floor: int = 0,
    ) -> int:
        """Calculate a score by deducting severity weights from a base."""
        score = base
        for finding in findings:
            score -= finding.severity.weight
        return max(floor, min(100, score))
