"""
VisionQA Rule System
======================
Pluggable rule architecture for analysis engines.

Instead of packing all logic into a single monolithic method,
engines register lightweight ``Rule`` objects.  Each rule:

1. Has a ``should_run(context)`` guard
2. Executes ``evaluate(context, state)`` → list of ``Finding``
3. Can be individually enabled/disabled or swapped at runtime

The ``RuleEngine`` orchestrates rule execution with error isolation —
if one rule crashes, the rest still run.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, TypeVar

from core.interfaces.exceptions import RuleExecutionError
from core.interfaces.types import (
    AnalysisContext,
    Finding,
    Severity,
)

logger = logging.getLogger("visionqa.rules")

# Generic type for rule-specific shared state
T = TypeVar("T")


class Rule(ABC):
    """
    A single analysis rule.

    Each rule is a focused, self-contained check.  Rules are registered
    into a ``RuleEngine`` which runs them in order with error isolation.
    """

    # --- Identity ---
    name: str = ""
    category: str = ""
    description: str = ""
    enabled: bool = True

    def should_run(self, context: AnalysisContext) -> bool:
        """Return False to skip this rule for the given context."""
        return self.enabled

    @abstractmethod
    def evaluate(
        self,
        context: AnalysisContext,
        state: Dict[str, Any],
    ) -> List[Finding]:
        """
        Run the check and return zero or more findings.

        Parameters
        ----------
        context : AnalysisContext
            The analysis input.
        state : dict
            Shared mutable state that rules can read from and write to.
            This allows earlier rules to pass computed data (e.g., detected
            text regions, parsed headers) to later rules without recomputation.

        Returns
        -------
        list[Finding]
            Zero or more findings.  Return an empty list for "pass".
        """
        raise NotImplementedError


@dataclass
class RuleResult:
    """Outcome of running one rule."""

    rule_name: str
    findings: List[Finding] = field(default_factory=list)
    error: Optional[str] = None
    skipped: bool = False


class RuleEngine:
    """
    Orchestrates execution of a list of rules with error isolation.

    Usage::

        engine = RuleEngine()
        engine.register(PIIExposureRule())
        engine.register(DebugPageRule())

        results = engine.run_all(context)
        all_findings = results.all_findings
    """

    def __init__(self) -> None:
        self._rules: List[Rule] = []
        self._logger = logging.getLogger("visionqa.rules")

    def register(self, rule: Rule) -> "RuleEngine":
        """Register a rule.  Returns self for chaining."""
        self._rules.append(rule)
        return self

    def register_many(self, rules: List[Rule]) -> "RuleEngine":
        """Register multiple rules.  Returns self for chaining."""
        self._rules.extend(rules)
        return self

    @property
    def rules(self) -> List[Rule]:
        return list(self._rules)

    def run_all(
        self,
        context: AnalysisContext,
        state: Optional[Dict[str, Any]] = None,
    ) -> "RuleEngineResult":
        """
        Execute all registered rules with error isolation.

        If a rule raises, the error is captured and remaining rules
        continue executing.
        """
        if state is None:
            state = {}

        results: List[RuleResult] = []
        finding_id_counter = 1

        for rule in self._rules:
            # Guard
            if not rule.should_run(context):
                results.append(
                    RuleResult(rule_name=rule.name, skipped=True)
                )
                continue

            # Execute with isolation
            try:
                findings = rule.evaluate(context, state)
                # Assign sequential IDs
                for finding in findings:
                    finding.id = finding_id_counter
                    finding_id_counter += 1
                results.append(
                    RuleResult(rule_name=rule.name, findings=findings)
                )
            except Exception as exc:
                self._logger.warning(
                    "Rule '%s' failed: %s",
                    rule.name,
                    exc,
                    exc_info=True,
                )
                results.append(
                    RuleResult(rule_name=rule.name, error=str(exc))
                )

        return RuleEngineResult(results=results)


@dataclass
class RuleEngineResult:
    """Aggregated results from a rule engine run."""

    results: List[RuleResult] = field(default_factory=list)

    @property
    def all_findings(self) -> List[Finding]:
        """Flat list of findings from all rules."""
        return [
            finding
            for result in self.results
            for finding in result.findings
        ]

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.error)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.skipped)

    @property
    def executed_count(self) -> int:
        return sum(
            1 for r in self.results if not r.skipped and r.error is None
        )
