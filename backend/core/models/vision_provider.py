import os
import asyncio
from typing import Any, Dict, List, Optional, Tuple


class VisionProviderManager:
    """
    Lazy visual provider facade.

    Default order is SAM3 first, then Grounding DINO. Providers are imported and
    instantiated only when a visual analysis call needs them, so CI can import
    modules without model downloads.
    """

    PROVIDER_NAMES = {
        "sam3": "SAM3",
        "dinox": "Grounding DINO",
        "grounding_dino": "Grounding DINO",
        "grounding-dino": "Grounding DINO",
    }

    def __init__(
        self,
        primary: Optional[str] = None,
        fallback: Optional[str] = None,
    ):
        self.primary = self._normalize_provider(
            primary if primary is not None else os.getenv("VISION_MODEL_PROVIDER", "sam3")
        )
        self.fallback = self._normalize_provider(
            fallback if fallback is not None else os.getenv("VISION_MODEL_FALLBACK", "dinox")
        )
        self._clients: Dict[str, Any] = {}
        self.last_error: Optional[str] = None
        self.last_provider: Optional[str] = None
        self.timeout_seconds = float(os.getenv("VISION_PROVIDER_TIMEOUT_SECONDS", "90"))

    def _normalize_provider(self, provider: Optional[str]) -> str:
        value = (provider or "").strip().lower().replace(" ", "_")
        if value in {"", "none", "off", "disabled", "false", "0"}:
            return "none"
        if value in {"dino", "dinox", "grounding_dino", "grounding-dino"}:
            return "dinox"
        if value in {"sam", "sam3"}:
            return "sam3"
        return value

    def _ordered_providers(self) -> List[str]:
        providers: List[str] = []
        for provider in [self.primary, self.fallback]:
            if provider == "none" or provider in providers:
                continue
            providers.append(provider)
        return providers

    def _display_name(self, provider: str) -> str:
        return self.PROVIDER_NAMES.get(provider, provider)

    def _get_client(self, provider: str) -> Any:
        if provider in self._clients:
            return self._clients[provider]

        if provider == "sam3":
            from core.models.sam3_client import SAM3Client

            client = SAM3Client()
        elif provider == "dinox":
            from core.models.dinox_client import DINOXClient

            client = DINOXClient()
        else:
            raise ValueError(f"Unknown vision provider: {provider}")

        self._clients[provider] = client
        return client

    async def detect_elements(
        self,
        screenshot_path: str,
        prompt: Optional[str] = None,
        require_results: bool = False,
    ) -> Tuple[List[Dict[str, Any]], str]:
        self.last_error = None
        self.last_provider = None

        for provider in self._ordered_providers():
            provider_name = self._display_name(provider)
            try:
                client = self._get_client(provider)
                if prompt is None:
                    elements = await asyncio.wait_for(
                        client.detect_elements(screenshot_path),
                        timeout=self.timeout_seconds,
                    )
                else:
                    elements = await asyncio.wait_for(
                        client.detect_elements(screenshot_path, prompt=prompt),
                        timeout=self.timeout_seconds,
                    )
                provider_error = getattr(client, "last_error", None)
                if provider_error:
                    self.last_error = str(provider_error)
                if elements or not require_results:
                    self.last_provider = provider_name
                    return elements or [], provider_name
                self.last_error = self.last_error or "provider returned no visual elements"
            except Exception as exc:
                self.last_error = str(exc)
                continue

        self.last_provider = "none"
        return [], "none"

    async def detect_obstacles(self, screenshot_path: str) -> Tuple[List[Dict[str, Any]], str]:
        self.last_error = None
        for provider in self._ordered_providers():
            provider_name = self._display_name(provider)
            try:
                client = self._get_client(provider)
                if hasattr(client, "detect_obstacles"):
                    elements = await client.detect_obstacles(screenshot_path)
                else:
                    prompt = getattr(client, "OBSTACLES_PROMPT", None)
                    elements = await client.detect_elements(screenshot_path, prompt=prompt)
                if elements:
                    self.last_provider = provider_name
                    return elements, provider_name
            except Exception as exc:
                self.last_error = str(exc)
                continue
        self.last_provider = "none"
        return [], "none"

    async def get_world_view(self, screenshot_path: str) -> Tuple[str, str]:
        elements, provider = await self.detect_elements(screenshot_path, require_results=True)
        if not elements:
            return "No UI elements detected visually.", provider

        lines = [f"### VISUAL WORLD VIEW (Detected via {provider})"]
        for index, elem in enumerate(elements, 1):
            label = elem.get("label", "element")
            box = elem.get("box", [])
            score = elem.get("score", 0)
            lines.append(f"{index}. [{label}] at {box} (confidence: {score:.2f})")
        return "\n".join(lines), provider
