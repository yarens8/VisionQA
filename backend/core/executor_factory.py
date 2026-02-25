from __future__ import annotations

from typing import Any

from core.interfaces.executor import Platform, PlatformExecutor
from executors.api.api_executor import APIExecutor
from executors.database.db_executor import DatabaseExecutor
from executors.desktop.desktop_executor import DesktopExecutor
from executors.mobile.mobile_executor import MobileExecutor
from executors.web.web_executor import WebExecutor


class _WebExecutorAdapter(PlatformExecutor):
    def __init__(self, executor: WebExecutor):
        self.executor = executor

    async def start(self) -> bool:
        await self.executor.start()
        return True

    async def stop(self) -> bool:
        await self.executor.stop()
        return True


class _MobileExecutorAdapter(PlatformExecutor):
    def __init__(self, executor: MobileExecutor):
        self.executor = executor

    async def start(self) -> bool:
        return await self.executor.start()

    async def stop(self) -> bool:
        return await self.executor.stop()


class _DesktopExecutorAdapter(PlatformExecutor):
    def __init__(self, executor: DesktopExecutor):
        self.executor = executor

    async def start(self) -> bool:
        return await self.executor.start()

    async def stop(self) -> bool:
        return await self.executor.stop()


class _APIExecutorAdapter(PlatformExecutor):
    def __init__(self, executor: APIExecutor):
        self.executor = executor

    async def start(self) -> bool:
        return True

    async def stop(self) -> bool:
        await self.executor.close()
        return True


class _DatabaseExecutorAdapter(PlatformExecutor):
    def __init__(self, executor: DatabaseExecutor):
        self.executor = executor

    async def start(self) -> bool:
        return True

    async def stop(self) -> bool:
        try:
            self.executor.engine.dispose()
        except Exception:
            return False
        return True


class ExecutorFactory:
    """Create platform executors with a unified contract."""

    @staticmethod
    def create_executor(platform: Platform | str, **kwargs: Any) -> PlatformExecutor:
        if isinstance(platform, str):
            platform = Platform(platform)

        if platform == Platform.WEB:
            raw = WebExecutor(headless=kwargs.get("headless", True))
            return _WebExecutorAdapter(raw)

        if platform == Platform.MOBILE_ANDROID:
            raw = MobileExecutor(
                platform="android",
                device_name=kwargs.get("device_name", "emulator-5554"),
                appium_server_url=kwargs.get("appium_server_url", "http://localhost:4723"),
                automation_name=kwargs.get("automation_name"),
                app_package=kwargs.get("app_package"),
                app_activity=kwargs.get("app_activity"),
            )
            return _MobileExecutorAdapter(raw)

        if platform == Platform.MOBILE_IOS:
            raw = MobileExecutor(
                platform="ios",
                device_name=kwargs.get("device_name", "ios-simulator"),
                appium_server_url=kwargs.get("appium_server_url", "http://localhost:4723"),
                automation_name=kwargs.get("automation_name"),
                bundle_id=kwargs.get("bundle_id"),
            )
            return _MobileExecutorAdapter(raw)

        if platform == Platform.DESKTOP_WINDOWS:
            raw = DesktopExecutor(platform="windows")
            return _DesktopExecutorAdapter(raw)

        if platform == Platform.API:
            raw = APIExecutor(
                base_url=kwargs.get("base_url"),
                headers=kwargs.get("headers"),
            )
            return _APIExecutorAdapter(raw)

        if platform == Platform.DATABASE:
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise ValueError("DATABASE platform requires 'connection_string'.")
            raw = DatabaseExecutor(connection_string=connection_string)
            return _DatabaseExecutorAdapter(raw)

        raise ValueError(f"Unsupported platform: {platform}")
