
from __future__ import annotations

import io
import subprocess
from typing import Optional

class DesktopExecutor:
    """
    VisionQA Desktop Executor (Windows First).
    Provides minimal real desktop automation flow.
    """

    def __init__(self, platform: str = "windows"):
        self.platform = platform.lower()
        self.process: Optional[subprocess.Popen] = None

    async def start(self) -> bool:
        """Initialize desktop executor runtime."""
        if self.platform != "windows":
            raise ValueError(f"Unsupported desktop platform: {self.platform}")
        return True

    async def launch_app(self, app_path: str) -> bool:
        """Launch desktop application."""
        self.process = subprocess.Popen(app_path)
        print(f"[DesktopExecutor] App launched: {app_path} (pid={self.process.pid})")
        return True

    async def click_element(self, element_name: str) -> bool:
        """
        Minimal click support.
        Accepts coordinate format: "x,y" and clicks via pyautogui.
        """
        try:
            import pyautogui  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "pyautogui is required for click actions. Install it or use WinAppDriver integration."
            ) from exc

        parts = [p.strip() for p in element_name.split(",")]
        if len(parts) != 2:
            raise ValueError("element_name must be coordinate string in 'x,y' format.")

        x, y = int(parts[0]), int(parts[1])
        pyautogui.click(x=x, y=y)
        print(f"[DesktopExecutor] Clicked at ({x}, {y})")
        return True

    async def type_text(self, text: str) -> bool:
        """Type text using keyboard events."""
        try:
            import pyautogui  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "pyautogui is required for keyboard input. Install it or use WinAppDriver integration."
            ) from exc
        pyautogui.write(text, interval=0.03)
        print(f"[DesktopExecutor] Typed text ({len(text)} chars).")
        return True

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """Capture desktop screenshot and optionally persist PNG file."""
        try:
            import pyautogui  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "pyautogui is required for screenshot actions. Install it or use WinAppDriver integration."
            ) from exc

        image = pyautogui.screenshot()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()

        if path:
            with open(path, "wb") as f:
                f.write(png_bytes)
            print(f"[DesktopExecutor] Screenshot saved: {path}")

        return png_bytes

    async def stop(self) -> bool:
        """Terminate launched application process if present."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("[DesktopExecutor] App process terminated.")
        self.process = None
        return True
