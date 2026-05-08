"""
VisionQA Core Interfaces
==========================
Public API surface for the core framework.

Modules import from here::

    from core.interfaces import (
        BaseAnalyzerEngine,
        AnalysisContext,
        AnalysisResult,
        Finding,
        Rule,
        RuleEngine,
        Severity,
        ModuleName,
        get_settings,
    )
"""

from core.interfaces.engine import BaseAnalyzerEngine
from core.interfaces.exceptions import (
    AnalysisError,
    ConfigurationError,
    EngineNotReadyError,
    ExecutorError,
    ExecutorTimeoutError,
    ExternalServiceError,
    ExternalServiceTimeoutError,
    ImageProcessingError,
    RuleExecutionError,
    TextExtractionError,
    UnsupportedPlatformError,
    VisionQAException,
)
from core.interfaces.executor import Platform, PlatformExecutor
from core.interfaces.rules import Rule, RuleEngine, RuleEngineResult, RuleResult
from core.interfaces.settings import VisionQASettings, get_settings
from core.interfaces.types import (
    AnalysisContext,
    AnalysisLayer,
    AnalysisResult,
    BoundingBox,
    Finding,
    ModuleName,
    ScoreBreakdown,
    Severity,
)

__all__ = [
    # Engine
    "BaseAnalyzerEngine",
    # Types
    "AnalysisContext",
    "AnalysisLayer",
    "AnalysisResult",
    "BoundingBox",
    "Finding",
    "ModuleName",
    "ScoreBreakdown",
    "Severity",
    # Rules
    "Rule",
    "RuleEngine",
    "RuleEngineResult",
    "RuleResult",
    # Executor
    "Platform",
    "PlatformExecutor",
    # Settings
    "VisionQASettings",
    "get_settings",
    # Exceptions
    "AnalysisError",
    "ConfigurationError",
    "EngineNotReadyError",
    "ExecutorError",
    "ExecutorTimeoutError",
    "ExternalServiceError",
    "ExternalServiceTimeoutError",
    "ImageProcessingError",
    "RuleExecutionError",
    "TextExtractionError",
    "UnsupportedPlatformError",
    "VisionQAException",
]
