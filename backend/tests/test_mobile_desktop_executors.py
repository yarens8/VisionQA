import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from executors.desktop.desktop_executor import DesktopExecutor
from executors.mobile.mobile_executor import MobileExecutor


@pytest.mark.asyncio
async def test_mobile_initialize_alias_starts_session():
    executor = MobileExecutor()

    status_response = MagicMock()
    status_response.raise_for_status = MagicMock()
    executor.client.get = AsyncMock(return_value=status_response)

    response = MagicMock()
    response.json.return_value = {"sessionId": "abc-123"}
    response.raise_for_status = MagicMock()
    executor.client.post = AsyncMock(return_value=response)

    started = await executor.initialize()

    assert started is True
    assert executor.session_id == "abc-123"


@pytest.mark.asyncio
async def test_mobile_start_raises_clear_error_when_appium_unreachable():
    executor = MobileExecutor()
    executor.client.get = AsyncMock(side_effect=Exception("connection failed"))

    with pytest.raises(RuntimeError, match="Appium server is not reachable"):
        await executor.start()


@pytest.mark.asyncio
async def test_mobile_swipe_posts_w3c_actions():
    executor = MobileExecutor()
    executor.session_id = "session-1"

    response = MagicMock()
    response.raise_for_status = MagicMock()
    executor.client.post = AsyncMock(return_value=response)

    result = await executor.swipe(10, 20, 30, 40, duration_ms=500)

    assert result is True
    assert executor.client.post.await_count == 1
    _, kwargs = executor.client.post.await_args
    payload = kwargs["json"]
    swipe_action = payload["actions"][0]["actions"][3]
    assert swipe_action["x"] == 30
    assert swipe_action["y"] == 40
    assert swipe_action["duration"] == 500


@pytest.mark.asyncio
async def test_desktop_screenshot_returns_png_bytes(monkeypatch):
    image = MagicMock()
    image.save = MagicMock(side_effect=lambda buffer, format: buffer.write(b"png-bytes"))

    fake_pyautogui = SimpleNamespace(screenshot=lambda: image)
    monkeypatch.setitem(sys.modules, "pyautogui", fake_pyautogui)

    executor = DesktopExecutor()
    png_bytes = await executor.screenshot()

    assert png_bytes == b"png-bytes"
