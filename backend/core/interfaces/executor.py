from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict


class Platform(str, Enum):
    WEB = "web"
    MOBILE_ANDROID = "mobile_android"
    MOBILE_IOS = "mobile_ios"
    DESKTOP_WINDOWS = "desktop_windows"
    API = "api"
    DATABASE = "database"


class PlatformExecutor(ABC):
    """Common contract for all platform executors."""

    @abstractmethod
    async def start(self) -> bool:
        """Initialize executor resources."""
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> bool:
        """Release executor resources."""
        raise NotImplementedError

    async def health_check(self) -> Dict[str, Any]:
        """Optional readiness check used by orchestration/smoke tests."""
        return {"ready": True}

