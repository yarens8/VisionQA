"""
VAD Router — Visual Anomaly Detection API
=============================================
Endpoints for running visual anomaly detection on screenshots.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from core.vad.engine import VADEngine

router = APIRouter(prefix="/vad", tags=["Visual Anomaly Detection"])

# Singleton engine
_engine = VADEngine()


class VADAnalyzeRequest(BaseModel):
    """Request body for VAD analysis."""
    url: Optional[str] = None
    screenshot_base64: Optional[str] = None
    viewport_width: int = 1280
    viewport_height: int = 720


class VADFromURLRequest(BaseModel):
    """Request body for URL-based VAD analysis."""
    url: str
    viewport_width: int = 1280
    viewport_height: int = 720


@router.post("/analyze")
async def analyze_screenshot(request: VADAnalyzeRequest) -> Dict[str, Any]:
    """
    🔍 Gorsel Anomali Tespiti — Screenshot Analizi

    Base64 formatinda ekran goruntusu gonder,
    gorsel bozukluklari (cakisma, tasma, hizalama, kirik gorsel) tespit et.
    """
    if not request.screenshot_base64:
        raise HTTPException(
            status_code=400,
            detail="screenshot_base64 alani zorunlu."
        )

    try:
        report = await _engine.analyze(
            screenshot_base64=request.screenshot_base64,
            url=request.url,
            viewport_width=request.viewport_width,
            viewport_height=request.viewport_height,
        )
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAD analiz hatasi: {str(e)}")


@router.post("/analyze-url")
async def analyze_url(request: VADFromURLRequest) -> Dict[str, Any]:
    """
    🌐 Gorsel Anomali Tespiti — URL Analizi

    Bir URL ver, sistem sayfayi acar, screenshot alir,
    gorsel bozukluklari otomatik tespit eder.
    """
    import os
    import tempfile

    url = request.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL http:// veya https:// ile baslamali.")

    executor = None
    screenshot_path = None

    try:
        from executors.web.web_executor import WebExecutor

        executor = WebExecutor(headless=True, highlight_enabled=False)
        await executor.start()
        await executor.navigate(url)

        # Extract DOM metadata for richer analysis
        dom_metadata = None
        try:
            dom_metadata = await executor.extract_accessibility_metadata()
        except Exception:
            pass

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        screenshot_path = tmp.name
        tmp.close()
        await executor.screenshot(screenshot_path, full_page=False)

        viewport = {"width": request.viewport_width, "height": request.viewport_height}
        if executor.page and executor.page.viewport_size:
            viewport = executor.page.viewport_size

        report = await _engine.analyze(
            screenshot_path=screenshot_path,
            url=url,
            dom_metadata=dom_metadata,
            viewport_width=viewport.get("width", request.viewport_width),
            viewport_height=viewport.get("height", request.viewport_height),
        )

        return report.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAD analiz hatasi: {str(e)}")
    finally:
        if executor:
            try:
                await executor.stop()
            except Exception:
                pass
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except Exception:
                pass
