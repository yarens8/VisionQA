import asyncio
import os
import shutil
import sys

import httpx
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from executors.api.api_executor import APIExecutor
from executors.database.db_executor import DatabaseExecutor
from executors.desktop.desktop_executor import DesktopExecutor
from executors.mobile.mobile_executor import MobileExecutor
from executors.web.web_executor import WebExecutor


BACKEND_URL = os.getenv("VISIONQA_BACKEND_URL", "http://localhost:8000")
APPIUM_URL = os.getenv("VISIONQA_APPIUM_URL", "http://localhost:4723")
DB_URL = os.getenv(
    "VISIONQA_DB_URL",
    "postgresql://visionqa:visionqa_dev_password@localhost:5432/visionqa_db",
)


def _require_smoke_enabled() -> None:
    if os.getenv("VISIONQA_RUN_SMOKE", "0") != "1":
        pytest.skip("Smoke tests are disabled. Set VISIONQA_RUN_SMOKE=1 to run.")


def _is_url_ready(url: str, timeout: float = 3.0) -> bool:
    try:
        resp = httpx.get(url, timeout=timeout)
        return resp.status_code < 500
    except Exception:
        return False


@pytest.mark.smoke
def test_smoke_backend_health():
    _require_smoke_enabled()
    response = httpx.get(f"{BACKEND_URL}/health", timeout=10)
    response.raise_for_status()
    body = response.json()
    assert body.get("status") == "ok"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_api_executor_httpbin():
    _require_smoke_enabled()
    executor = APIExecutor(base_url="https://httpbin.org")
    try:
        result = await executor.execute_step(method="GET", path="/get")
        assert result.get("success") is True
        assert result.get("status_code") == 200
    finally:
        await executor.close()


@pytest.mark.smoke
def test_smoke_database_executor():
    _require_smoke_enabled()
    executor = DatabaseExecutor(connection_string=DB_URL)
    result = executor.execute_query("SELECT 1 AS ok")
    assert result.get("success") is True
    assert result.get("row_count") == 1


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_web_executor():
    _require_smoke_enabled()
    executor = WebExecutor(headless=True)
    try:
        await executor.start()
        await executor.navigate("https://example.com")
        screenshot = await executor.screenshot()
        assert isinstance(screenshot, bytes)
        assert len(screenshot) > 0
    finally:
        await executor.stop()


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_mobile_executor():
    _require_smoke_enabled()
    if not _is_url_ready(f"{APPIUM_URL}/status"):
        pytest.skip(f"Appium not ready at {APPIUM_URL}")

    executor = MobileExecutor(
        platform="android",
        device_name=os.getenv("VISIONQA_ANDROID_DEVICE", "emulator-5554"),
        appium_server_url=APPIUM_URL,
        app_package=os.getenv("VISIONQA_ANDROID_APP_PACKAGE", "com.android.settings"),
        app_activity=os.getenv("VISIONQA_ANDROID_APP_ACTIVITY", ".Settings"),
    )
    try:
        await executor.start()
        # Make mobile smoke visibly confirmable on emulator.
        screenshot_b64 = await executor.screenshot()
        await executor.tap(200, 500)
        await executor.swipe(300, 1200, 300, 700, duration_ms=400)
        pause_sec = float(os.getenv("VISIONQA_MOBILE_SMOKE_PAUSE_SEC", "2.0"))
        if pause_sec > 0:
            await asyncio.sleep(pause_sec)
        assert isinstance(screenshot_b64, str)
        assert len(screenshot_b64) > 0
    finally:
        await executor.stop()


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_desktop_executor():
    _require_smoke_enabled()
    if shutil.which("notepad.exe") is None:
        pytest.skip("Notepad is not available on this machine")

    executor = DesktopExecutor()
    await executor.start()
    try:
        await executor.launch_app("notepad.exe")
        await asyncio.sleep(0.4)
        await executor.type_text("VisionQA smoke test")
        screenshot = await executor.screenshot()
        assert isinstance(screenshot, bytes)
        assert len(screenshot) > 0
    finally:
        await executor.stop()
