
from playwright.async_api import async_playwright, Browser, Page
from typing import Optional
import base64

class WebExecutor:
    """
    Web Tarayıcı Executor (Playwright)
    Görev: Siteleri açmak, tıklamak, screenshot almak.
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def start(self):
        """Tarayıcıyı başlat"""
        print(f"🎭 [WebExecutor] Tarayıcı başlatılıyor (Headless: {self.headless})...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        print("✅ [WebExecutor] Tarayıcı hazır!")
    
    async def navigate(self, url: str):
        """Belirtilen URL'e git"""
        if not self.page:
            raise Exception("Tarayıcı başlatılmamış! Önce start() çağırın.")
        
        print(f"🌐 [WebExecutor] Gidiliyor: {url}")
        await self.page.goto(url, wait_until="networkidle")
        print(f"✅ [WebExecutor] Sayfa yüklendi: {self.page.url}")
    
    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """
        Ekran görüntüsü al
        Returns: Screenshot bytes (PNG format)
        """
        if not self.page:
            raise Exception("Sayfa yok!")
        
        screenshot_bytes = await self.page.screenshot(full_page=True)
        
        if path:
            with open(path, "wb") as f:
                f.write(screenshot_bytes)
            print(f"📸 [WebExecutor] Screenshot kaydedildi: {path}")
        
        return screenshot_bytes
    
    async def click(self, x: int, y: int):
        """Verilen koordinata tıkla"""
        if not self.page:
            raise Exception("Sayfa yok!")
        
        print(f"👆 [WebExecutor] Tıklanıyor: ({x}, {y})")
        await self.page.mouse.click(x, y)
    
    async def type_text(self, text: str):
        """Klavyeden yazı yaz"""
        if not self.page:
            raise Exception("Sayfa yok!")
        
        print(f"⌨️ [WebExecutor] Yazılıyor: {text}")
        await self.page.keyboard.type(text)
    
    async def stop(self):
        """Tarayıcıyı kapat"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("🛑 [WebExecutor] Tarayıcı kapatıldı.")
