
from __future__ import annotations

import asyncio
import io
import os
import subprocess
from typing import Any, Dict, Optional


class DesktopExecutor:
    """
    VisionQA Desktop Executor (Windows First).
    Provides minimal real desktop automation flow.
    """

    def __init__(self, platform: str = "windows"):
        self.platform = platform.lower()
        self.process: Optional[subprocess.Popen] = None
        self._hwnd: Optional[int] = None  # Win32 window handle

    async def start(self) -> bool:
        """Initialize desktop executor runtime."""
        if self.platform != "windows":
            raise ValueError(f"Unsupported desktop platform: {self.platform}")
        return True

    # ── Window Focus Management ────────────────────────────────────

    def _find_window_by_pid(self, pid: int) -> Optional[int]:
        """Find the main window handle for a given process ID."""
        try:
            import win32gui  # type: ignore
            import win32process  # type: ignore
        except ImportError:
            return None

        result: Optional[int] = None

        def _enum_callback(hwnd: int, _: None) -> None:
            nonlocal result
            if not win32gui.IsWindowVisible(hwnd):
                return
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                result = hwnd

        win32gui.EnumWindows(_enum_callback, None)
        return result

    def _focus_app_window(self) -> bool:
        """Bring the launched application window to the foreground.

        Returns True if the window was successfully focused.
        Falls back gracefully when pywin32 is not installed.
        """
        if self.process is None:
            return False

        # Try cached handle first
        hwnd = self._hwnd or self._find_window_by_pid(self.process.pid)
        if hwnd is None:
            return False

        self._hwnd = hwnd
        try:
            import win32gui  # type: ignore
            import win32con  # type: ignore

            # Restore if minimised, then bring to front
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            print(f"[DesktopExecutor] Window focused (hwnd={hwnd})")
            return True
        except Exception as exc:
            print(f"[DesktopExecutor] Focus fallback — {exc}")
            return False

    # ── App Lifecycle ──────────────────────────────────────────────

    async def launch_app(self, app_path: str) -> bool:
        """Launch desktop application and wait for its window to appear."""
        self.process = subprocess.Popen(app_path)
        print(f"[DesktopExecutor] App launched: {app_path} (pid={self.process.pid})")

        # Give the app time to create its window, then grab the handle
        for _ in range(10):
            await asyncio.sleep(0.3)
            hwnd = self._find_window_by_pid(self.process.pid)
            if hwnd:
                self._hwnd = hwnd
                self._focus_app_window()
                break

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

        self._focus_app_window()

        parts = [p.strip() for p in element_name.split(",")]
        if len(parts) != 2:
            raise ValueError("element_name must be coordinate string in 'x,y' format.")

        x, y = int(parts[0]), int(parts[1])
        pyautogui.click(x=x, y=y)
        print(f"[DesktopExecutor] Clicked at ({x}, {y})")
        return True

    async def type_text(self, text: str) -> bool:
        """Type text into the launched application window."""
        try:
            import pyautogui  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "pyautogui is required for keyboard input. Install it or use WinAppDriver integration."
            ) from exc

        # Ensure the correct window has focus before typing
        self._focus_app_window()
        await asyncio.sleep(0.15)

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

    @staticmethod
    def _infer_desktop_element_type(control_type: str, class_name: str) -> str:
        normalized_type = (control_type or "").strip().lower()
        normalized_class = (class_name or "").strip().lower()

        if "edit" in normalized_type or "edit" in normalized_class:
            return "input"
        if "button" in normalized_type or "button" in normalized_class:
            return "button"
        if "hyperlink" in normalized_type or "link" in normalized_type:
            return "link"
        if "image" in normalized_type or "image" in normalized_class:
            return "image"
        if "checkbox" in normalized_type:
            return "checkbox"
        if "radio" in normalized_type:
            return "radio"
        if "text" in normalized_type:
            return "text"
        return "element"

    async def extract_accessibility_metadata(self) -> list[Dict[str, Any]]:
        """Best-effort accessibility metadata extraction for Windows desktop apps."""
        if self.platform != "windows":
            return []

        if self.process is None and self._hwnd is None:
            return []

        try:
            from pywinauto import Application  # type: ignore
        except Exception:
            return []

        hwnd = self._hwnd or (self._find_window_by_pid(self.process.pid) if self.process else None)
        if hwnd is None:
            return []

        try:
            app = Application(backend="uia").connect(handle=hwnd)
            window = app.window(handle=hwnd)
            descendants = [window] + list(window.descendants())
        except Exception:
            return []

        metadata: list[Dict[str, Any]] = []
        for element in descendants:
            try:
                rectangle = element.rectangle()
                width = max(1, int(rectangle.width()))
                height = max(1, int(rectangle.height()))
                if width <= 0 or height <= 0:
                    continue

                element_info = getattr(element, "element_info", None)
                control_type = getattr(element_info, "control_type", "") or ""
                class_name = getattr(element_info, "class_name", "") or ""
                name = getattr(element_info, "name", "") or ""
                automation_id = getattr(element_info, "automation_id", "") or ""

                metadata.append(
                    {
                        "element_type": self._infer_desktop_element_type(control_type, class_name),
                        "x": int(rectangle.left),
                        "y": int(rectangle.top),
                        "width": width,
                        "height": height,
                        "text_content": str(name).strip() or None,
                        "name": str(automation_id).strip() or None,
                        "keyboard_focusable": None,
                        "focus_visible": None,
                    }
                )
            except Exception:
                continue

        return metadata

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
        self._hwnd = None
        return True
