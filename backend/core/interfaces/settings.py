"""
VisionQA Configuration
========================
Centralized, environment-aware settings using pydantic-settings.

All hardcoded paths, API keys, and thresholds live here instead of
being scattered across engine files.

Usage::

    from core.interfaces.settings import get_settings
    settings = get_settings()
    print(settings.tesseract_cmd)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VisionQASettings(BaseSettings):
    """
    Application-wide configuration.

    Values are loaded from environment variables and ``.env`` file.
    Each setting has a sensible default so the app starts with zero config.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="VISIONQA_",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    debug: bool = False
    log_level: str = "INFO"
    environment: str = "development"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = "sqlite:///./visionqa_temp.db"

    # ------------------------------------------------------------------
    # LLM / AI Services
    # ------------------------------------------------------------------
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o"
    dinox_api_key: Optional[str] = Field(default=None, alias="DINOX_API_KEY")

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------
    tesseract_cmd: Optional[str] = None

    # Default search paths for Tesseract on Windows
    tesseract_search_paths: list[str] = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    # ------------------------------------------------------------------
    # Analysis Thresholds
    # ------------------------------------------------------------------

    # Accessibility
    wcag_aa_contrast_ratio: float = 4.5
    wcag_aaa_contrast_ratio: float = 7.0
    min_touch_target_px: int = 44
    mobile_touch_target_px: int = 48

    # Security
    max_security_findings: int = 10
    max_attack_hypotheses: int = 6

    # Performance
    lcp_threshold_ms: float = 2500.0
    fcp_threshold_ms: float = 1800.0
    cls_threshold: float = 0.12
    api_p95_threshold_ms: float = 1200.0
    db_slow_query_ms: float = 220.0

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    def resolve_tesseract_cmd(self) -> Optional[str]:
        """Find the Tesseract binary using config, env, PATH, or defaults."""
        import shutil

        # 1. Explicit setting
        if self.tesseract_cmd and os.path.exists(self.tesseract_cmd):
            return self.tesseract_cmd

        # 2. Environment override
        env_path = os.environ.get("TESSERACT_CMD", "").strip()
        if env_path and os.path.exists(env_path):
            return env_path

        # 3. System PATH
        discovered = shutil.which("tesseract")
        if discovered:
            return discovered

        # 4. Common install locations
        for candidate in self.tesseract_search_paths:
            if os.path.exists(candidate):
                return candidate

        return None


@lru_cache(maxsize=1)
def get_settings() -> VisionQASettings:
    """
    Return the singleton settings instance.

    Cached so repeated calls don't re-parse environment/files.
    """
    return VisionQASettings()
