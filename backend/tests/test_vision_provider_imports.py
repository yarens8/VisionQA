import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models.sam3_client import SAM3Client
from core.models.dinox_client import DINOXClient
from core.models.vision_provider import VisionProviderManager
from core.agents.case_generator import AICaseGenerator


def test_sam3_client_is_available_as_primary_vision_provider_import():
    assert SAM3Client.__name__ == "SAM3Client"
    assert hasattr(SAM3Client, "DEFAULT_PROMPT")
    assert "button" in SAM3Client.DEFAULT_PROMPT


def test_grounding_dino_client_is_available_as_fallback_vision_provider_import():
    assert DINOXClient.__name__ == "DINOXClient"
    assert hasattr(DINOXClient, "DEFAULT_PROMPT")
    assert "button" in DINOXClient.DEFAULT_PROMPT


class _EmptySAM3:
    last_error = "model unavailable"

    async def detect_elements(self, screenshot_path, prompt=None):
        return []


class _FallbackDINO:
    async def detect_elements(self, screenshot_path, prompt=None):
        return [{"label": "button", "score": 0.8, "box": [1, 2, 30, 40]}]


@pytest.mark.asyncio
async def test_autonomous_tester_falls_back_to_dinox_when_sam3_has_no_result():
    generator = AICaseGenerator.__new__(AICaseGenerator)
    generator._vision = VisionProviderManager(primary="sam3", fallback="dinox")
    generator._vision._get_client = lambda provider: _EmptySAM3() if provider == "sam3" else _FallbackDINO()

    elements, provider = await generator._detect_visual_elements("screen.png")

    assert provider == "Grounding DINO"
    assert elements[0]["label"] == "button"


@pytest.mark.asyncio
async def test_vision_provider_can_be_disabled_without_model_imports():
    manager = VisionProviderManager(primary="none", fallback="none")

    elements, provider = await manager.detect_elements("screen.png")

    assert elements == []
    assert provider == "none"


@pytest.mark.asyncio
async def test_vision_provider_returns_empty_when_all_optional_providers_fail():
    manager = VisionProviderManager(primary="sam3", fallback="dinox")

    def fail_to_load(provider):
        raise RuntimeError(f"{provider} unavailable")

    manager._get_client = fail_to_load

    elements, provider = await manager.detect_elements("screen.png", require_results=True)

    assert elements == []
    assert provider == "none"
    assert "unavailable" in manager.last_error


@pytest.mark.asyncio
async def test_vision_provider_uses_primary_when_it_returns_elements():
    class _WorkingSAM3:
        last_error = None

        async def detect_elements(self, screenshot_path, prompt=None):
            return [{"label": "input field", "score": 0.9, "box": [1, 1, 20, 20]}]

    manager = VisionProviderManager(primary="sam3", fallback="dinox")
    manager._get_client = lambda provider: _WorkingSAM3()

    elements, provider = await manager.detect_elements("screen.png", require_results=True)

    assert provider == "SAM3"
    assert elements[0]["label"] == "input field"
