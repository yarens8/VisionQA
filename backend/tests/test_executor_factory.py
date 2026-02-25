import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.executor_factory import ExecutorFactory
from core.interfaces.executor import Platform


def test_factory_creates_all_core_platform_executors():
    executors = {
        Platform.WEB: ExecutorFactory.create_executor(Platform.WEB),
        Platform.MOBILE_ANDROID: ExecutorFactory.create_executor(Platform.MOBILE_ANDROID),
        Platform.DESKTOP_WINDOWS: ExecutorFactory.create_executor(Platform.DESKTOP_WINDOWS),
        Platform.API: ExecutorFactory.create_executor(Platform.API),
        Platform.DATABASE: ExecutorFactory.create_executor(
            Platform.DATABASE,
            connection_string="sqlite:///./visionqa_factory_test.db",
        ),
    }

    for platform, executor in executors.items():
        assert executor is not None, f"{platform} executor is None"


def test_factory_rejects_unknown_platform():
    with pytest.raises(ValueError):
        ExecutorFactory.create_executor("unknown_platform")

