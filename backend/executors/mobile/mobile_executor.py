
from __future__ import annotations

import asyncio
import shutil
import subprocess
from typing import Any, Dict, Optional

import httpx


class MobileExecutor:
    """
    VisionQA Mobile Executor (Appium HTTP Wrapper).
    Uses Appium's W3C WebDriver endpoints directly.
    """

    # Retry configuration for flaky emulator boots
    DEFAULT_MAX_RETRIES = 2
    DEVICE_BOOT_TIMEOUT = 60.0  # seconds to wait for sys.boot_completed

    def __init__(
        self,
        platform: str = "android",
        device_name: str = "emulator-5554",
        appium_server_url: str = "http://localhost:4723",
        automation_name: Optional[str] = None,
        app_package: Optional[str] = None,
        app_activity: Optional[str] = None,
        bundle_id: Optional[str] = None,
    ):
        self.platform = platform.lower()
        self.device_name = device_name
        self.appium_server_url = appium_server_url.rstrip("/")
        self.automation_name = automation_name
        self.app_package = app_package
        self.app_activity = app_activity
        self.bundle_id = bundle_id
        self.session_id: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=30.0)

    def _ensure_client(self) -> None:
        """Recreate HTTP client if it was closed by a previous stop()."""
        if self.client.is_closed:
            self.client = httpx.AsyncClient(timeout=30.0)

    async def _check_appium_status(self) -> None:
        """Fail fast with a clear error when Appium server is unreachable."""
        try:
            response = await self.client.get(f"{self.appium_server_url}/status")
            response.raise_for_status()
        except Exception as exc:
            raise RuntimeError(
                f"Appium server is not reachable at {self.appium_server_url}. "
                "Start Appium before running mobile tests."
            ) from exc

    # ── Device health helpers ──────────────────────────────────────────

    @staticmethod
    def _has_adb() -> bool:
        """Check whether *adb* is available on the PATH."""
        return shutil.which("adb") is not None

    async def _wait_for_device_boot(self) -> None:
        """Block until the Android emulator reports ``sys.boot_completed=1``.

        If *adb* is not on the PATH the check is silently skipped so that
        environments without the full Android SDK still work (Appium may be
        running on a remote host).
        """
        if not self._has_adb():
            return

        deadline = asyncio.get_event_loop().time() + self.DEVICE_BOOT_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            try:
                result = subprocess.run(
                    ["adb", "shell", "getprop", "sys.boot_completed"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.stdout.strip() == "1":
                    print("[MobileExecutor] Device boot confirmed.")
                    return
            except Exception:
                pass
            await asyncio.sleep(2)

        print(
            "[MobileExecutor] Warning: device boot check timed out after "
            f"{self.DEVICE_BOOT_TIMEOUT}s — proceeding anyway."
        )

    async def _cleanup_uiautomator2(self) -> None:
        """Force-stop stale UiAutomator2 processes on the device.

        This is called between retries to give Appium a clean slate for the
        next session attempt.
        """
        if not self._has_adb():
            return

        for pkg in (
            "io.appium.uiautomator2.server",
            "io.appium.uiautomator2.server.test",
        ):
            try:
                subprocess.run(
                    ["adb", "shell", "am", "force-stop", pkg],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass

    # ── Capabilities ───────────────────────────────────────────────────

    def _build_capabilities(self) -> Dict[str, Any]:
        if self.platform == "android":
            capabilities: Dict[str, Any] = {
                "platformName": "Android",
                "appium:deviceName": self.device_name,
                "appium:automationName": self.automation_name or "UiAutomator2",
                "appium:uiautomator2ServerLaunchTimeout": 60000,
                # Skip server reinstall when it already exists — speeds up retries
                "appium:skipServerInstallation": False,
            }
            if self.app_package:
                capabilities["appium:appPackage"] = self.app_package
            if self.app_activity:
                capabilities["appium:appActivity"] = self.app_activity
            return capabilities

        if self.platform == "ios":
            capabilities = {
                "platformName": "iOS",
                "appium:deviceName": self.device_name,
                "appium:automationName": self.automation_name or "XCUITest",
            }
            if self.bundle_id:
                capabilities["appium:bundleId"] = self.bundle_id
            return capabilities

        raise ValueError(f"Unsupported mobile platform: {self.platform}")

    # ── Session lifecycle ──────────────────────────────────────────────

    async def start(self, max_retries: int | None = None) -> bool:
        """Start Appium session with automatic retry for flaky emulator boots.

        On each failed attempt the executor cleans up stale UiAutomator2
        processes and waits a short back-off period before retrying.
        """
        retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        print(f"[MobileExecutor] Starting Appium session for {self.platform}...")
        self._ensure_client()
        await self._check_appium_status()

        # Wait for device boot before the first attempt
        if self.platform == "android":
            await self._wait_for_device_boot()

        payload = {
            "capabilities": {
                "alwaysMatch": self._build_capabilities(),
                "firstMatch": [{}],
            }
        }

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = await self.client.post(
                    f"{self.appium_server_url}/session",
                    json=payload,
                    timeout=90.0,
                )
                response.raise_for_status()
                data = response.json()

                session_id = data.get("sessionId") or data.get("value", {}).get(
                    "sessionId"
                )
                if not session_id:
                    raise RuntimeError(f"Appium session creation failed: {data}")

                self.session_id = session_id
                print(f"[MobileExecutor] Session ready: {self.session_id}")
                return True

            except (httpx.HTTPStatusError, httpx.ReadTimeout) as exc:
                last_error = exc
                if attempt < retries:
                    wait = 5 * (attempt + 1)
                    print(
                        f"[MobileExecutor] Attempt {attempt + 1}/{retries + 1} failed "
                        f"({type(exc).__name__}). Retrying in {wait}s…"
                    )
                    await self._cleanup_uiautomator2()
                    await asyncio.sleep(wait)
                else:
                    raise

        # Should never reach here, but satisfy type checker
        assert last_error is not None
        raise last_error

    async def initialize(self) -> bool:
        """Backward-compatible alias used by scenario steps/checklists."""
        return await self.start()

    async def tap(self, x: int, y: int) -> bool:
        """Tap a coordinate using W3C actions."""
        if not self.session_id:
            raise RuntimeError("Mobile session is not started.")

        actions_payload = {
            "actions": [
                {
                    "type": "pointer",
                    "id": "finger1",
                    "parameters": {"pointerType": "touch"},
                    "actions": [
                        {"type": "pointerMove", "duration": 0, "x": x, "y": y},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pause", "duration": 80},
                        {"type": "pointerUp", "button": 0},
                    ],
                }
            ]
        }
        response = await self.client.post(
            f"{self.appium_server_url}/session/{self.session_id}/actions",
            json=actions_payload,
        )
        response.raise_for_status()
        return True

    async def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 350,
    ) -> bool:
        """Swipe between coordinates using W3C actions."""
        if not self.session_id:
            raise RuntimeError("Mobile session is not started.")

        actions_payload = {
            "actions": [
                {
                    "type": "pointer",
                    "id": "finger1",
                    "parameters": {"pointerType": "touch"},
                    "actions": [
                        {"type": "pointerMove", "duration": 0, "x": start_x, "y": start_y},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pause", "duration": 50},
                        {
                            "type": "pointerMove",
                            "duration": max(0, duration_ms),
                            "x": end_x,
                            "y": end_y,
                        },
                        {"type": "pointerUp", "button": 0},
                    ],
                }
            ]
        }
        response = await self.client.post(
            f"{self.appium_server_url}/session/{self.session_id}/actions",
            json=actions_payload,
        )
        response.raise_for_status()
        return True

    async def screenshot(self) -> str:
        """
        Get screenshot as base64 string.
        """
        if not self.session_id:
            raise RuntimeError("Mobile session is not started.")

        response = await self.client.get(
            f"{self.appium_server_url}/session/{self.session_id}/screenshot"
        )
        response.raise_for_status()
        data = response.json().get("value")
        if not isinstance(data, str):
            raise RuntimeError("Invalid screenshot response from Appium.")
        return data

    async def stop(self) -> bool:
        """Stop Appium session and close HTTP client."""
        try:
            if self.session_id:
                await self.client.delete(f"{self.appium_server_url}/session/{self.session_id}")
                self.session_id = None
        finally:
            await self.client.aclose()
        print("[MobileExecutor] Session closed.")
        return True
