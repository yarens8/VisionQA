
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
    
    async def click_element(self, selector: str, timeout: int = 5000):
        """Verilen selector (ID/Class) üzerine tıkla"""
        if not self.page:
            raise Exception("Sayfa yok!")
        
        print(f"👆 [WebExecutor] Tıklanıyor: {selector}")
        try:
            elm = self.page.locator(selector).first
            await elm.wait_for(timeout=timeout)
            await elm.click()
            print(f"✅ Tıklandı: {selector}")
        except Exception as e:
            print(f"❌ Tıklama Hatası ({selector}): {str(e)}")
            raise e # Hatayı yukarı fırlat ki test runner yakalasın

    async def type_input(self, selector: str, text: str):
        """Input alanına yazı yaz"""
        if not self.page:
            raise Exception("Sayfa yok!")
        
        print(f"⌨️ [WebExecutor] Yazılıyor ({selector}): {text}")
        try:
            elm = self.page.locator(selector).first
            await elm.wait_for(timeout=3000)
            await elm.fill(text)
            print(f"✅ Yazıldı: {text}")
        except Exception as e:
            print(f"❌ Yazma Hatası ({selector}): {str(e)}")
            raise e

    async def verify_element(self, selector: str, timeout: int = 3000) -> bool:
        """Elementin varlığını kontrol et"""
        if not self.page:
            raise Exception("Sayfa yok!")
        
        print(f"🔍 [WebExecutor] Doğrulanıyor: {selector}")
        try:
            elm = self.page.locator(selector).first
            await elm.wait_for(timeout=timeout)
            is_visible = await elm.is_visible()
            if is_visible:
                print(f"✅ Element bulundu: {selector}")
                return True
            else:
                print(f"❌ Element görünür değil: {selector}")
                return False
        except Exception:
            print(f"❌ Element bulunamadı: {selector}")
            return False
    
    async def stop(self):
        """Tarayıcıyı kapat"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("🛑 [WebExecutor] Tarayıcı kapatıldı.")
