"""
VisionQA Custom Exceptions
============================
Domain-specific exception hierarchy.

All VisionQA modules raise exceptions from this hierarchy so that
routers and middleware can handle them uniformly.

Hierarchy
---------
VisionQAException                  ← base, never raised directly
├── AnalysisError                  ← generic analysis failure
│   ├── ImageProcessingError       ← PIL / screenshot decode failures
│   ├── TextExtractionError        ← OCR / text-region failures
│   └── RuleExecutionError         ← individual rule crashed
├── EngineNotReadyError            ← engine missing deps or config
├── UnsupportedPlatformError       ← unknown platform string
├── ExternalServiceError           ← LLM / DINO-X / remote API failures
│   └── ExternalServiceTimeoutError
├── ConfigurationError             ← bad .env / missing keys
└── ExecutorError                  ← Playwright / Appium / DB issues
    └── ExecutorTimeoutError
"""

from __future__ import annotations


class VisionQAException(Exception):
    """Base exception for every VisionQA error."""

    def __init__(self, message: str = "", *, details: str = ""):
        self.details = details
        super().__init__(message)


# ---------------------------------------------------------------------------
# Analysis errors
# ---------------------------------------------------------------------------


class AnalysisError(VisionQAException):
    """Raised when an analysis engine fails mid-flight."""


class ImageProcessingError(AnalysisError):
    """Raised when an image cannot be decoded or processed."""


class TextExtractionError(AnalysisError):
    """Raised when OCR or text-region extraction fails."""


class RuleExecutionError(AnalysisError):
    """Raised when a single analysis rule crashes.

    The engine can catch this and continue with remaining rules.
    """

    def __init__(self, rule_name: str, message: str = "", *, details: str = ""):
        self.rule_name = rule_name
        super().__init__(message or f"Rule '{rule_name}' failed", details=details)


# ---------------------------------------------------------------------------
# Engine lifecycle
# ---------------------------------------------------------------------------


class EngineNotReadyError(VisionQAException):
    """Raised when an engine is invoked before its dependencies are ready."""


class UnsupportedPlatformError(VisionQAException):
    """Raised when a platform string cannot be mapped to an engine."""

    def __init__(self, platform: str, *, details: str = ""):
        super().__init__(f"Unsupported platform: '{platform}'", details=details)


# ---------------------------------------------------------------------------
# External service errors
# ---------------------------------------------------------------------------


class ExternalServiceError(VisionQAException):
    """Raised when an LLM, vision API, or remote service call fails."""

    def __init__(self, service_name: str, message: str = "", *, details: str = ""):
        self.service_name = service_name
        super().__init__(
            message or f"External service '{service_name}' failed",
            details=details,
        )


class ExternalServiceTimeoutError(ExternalServiceError):
    """Raised when an external service call times out."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class ConfigurationError(VisionQAException):
    """Raised when required configuration is missing or invalid."""


# ---------------------------------------------------------------------------
# Executor errors
# ---------------------------------------------------------------------------


class ExecutorError(VisionQAException):
    """Raised when a platform executor (Playwright, Appium, DB) fails."""


class ExecutorTimeoutError(ExecutorError):
    """Raised when executor navigation or action times out."""
