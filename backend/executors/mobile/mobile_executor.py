
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class MobileExecutor:
    """
    VisionQA Mobile Executor (Appium HTTP Wrapper).
    Uses Appium's W3C WebDriver endpoints directly.
    """

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

    def _build_capabilities(self) -> Dict[str, Any]:
        if self.platform == "android":
            capabilities: Dict[str, Any] = {
                "platformName": "Android",
                "appium:deviceName": self.device_name,
                "appium:automationName": self.automation_name or "UiAutomator2",
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

    async def start(self) -> bool:
        """Start Appium session."""
        print(f"[MobileExecutor] Starting Appium session for {self.platform}...")
        self._ensure_client()
        await self._check_appium_status()

        payload = {
            "capabilities": {
                "alwaysMatch": self._build_capabilities(),
                "firstMatch": [{}],
            }
        }
        response = await self.client.post(f"{self.appium_server_url}/session", json=payload)
        response.raise_for_status()
        data = response.json()

        session_id = data.get("sessionId") or data.get("value", {}).get("sessionId")
        if not session_id:
            raise RuntimeError(f"Appium session creation failed: {data}")

        self.session_id = session_id
        print(f"[MobileExecutor] Session ready: {self.session_id}")
        return True

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
