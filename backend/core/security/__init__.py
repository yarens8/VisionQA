"""
VisionQA Security Module
===========================
Professional security analysis engine with pluggable rules,
context-aware hypothesis generation, and correlation analysis.
"""

from core.security.engine_v2 import SecurityEngineV2

# Legacy alias for backward compatibility
SecurityEngine = SecurityEngineV2

__all__ = ["SecurityEngine", "SecurityEngineV2"]
