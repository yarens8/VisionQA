
from playwright.async_api import async_playwright, Browser, Page
from typing import Optional
import asyncio
import re

class WebExecutor:
    """
    Web Tarayıcı Executor (Playwright)
    Görev: Siteleri açmak, tıklamak, screenshot almak.
    """
    
    def __init__(
        self,
        headless: bool = False,
        nav_retries: int = 1,
        nav_retry_delay_sec: float = 0.4,
        highlight_enabled: bool = True
    ):
        self.headless = headless
        self.nav_retries = max(0, nav_retries)
        self.nav_retry_delay_sec = max(0.0, nav_retry_delay_sec)
        self.highlight_enabled = highlight_enabled
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
        """Web sayfasını açar — Daha esnek yükleme stratejisi ile."""
        if not self.page:
            raise Exception("Tarayıcı başlatılmadı!")
        
        print(f"🌐 [WebExecutor] Gidiliyor: {url}")
        # 'domcontentloaded' ağır sayfalar için daha güvenlidir, timeout'u 60sn'ye çektik
        last_error: Optional[Exception] = None
        for attempt in range(1, self.nav_retries + 2):
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
                print(f"✅ [WebExecutor] Sayfa yüklendi: {url}")
                return
            except Exception as exc:
                last_error = exc
                if attempt <= self.nav_retries:
                    await asyncio.sleep(self.nav_retry_delay_sec)
                    continue
                break

        raise last_error if last_error else Exception(f"Navigation failed: {url}")
    
    async def screenshot(self, path: Optional[str] = None, full_page: bool = True) -> bytes:
        """
        Ekran görüntüsü al
        Returns: Screenshot bytes (PNG format)
        """
        if not self.page:
            raise Exception("Sayfa yok!")
        
        screenshot_bytes = await self.page.screenshot(full_page=full_page)
        
        if path:
            with open(path, "wb") as f:
                f.write(screenshot_bytes)
            print(f"📸 [WebExecutor] Screenshot kaydedildi: {path}")
        
        return screenshot_bytes
    
    async def highlight_element(self, selector_or_locator):
        """
        � Lazer İşaretleyici v6 (Ultra-Neon): Elementi kör edici bir parlaklıkla vurgular.
        """
        if not self.highlight_enabled:
            return
        if not self.page: return
        try:
            if hasattr(selector_or_locator, "element_handle"):
                handle = await selector_or_locator.element_handle()
            else:
                handle = await self.page.query_selector(selector_or_locator)

            if handle:
                await self.page.evaluate("""
                    (el) => {
                        if (el) {
                            // Eski lazerleri temizle
                            document.querySelectorAll('.visionqa-target').forEach(e => e.remove());
                            
                            const rect = el.getBoundingClientRect();
                            const overlay = document.createElement('div');
                            overlay.className = 'visionqa-ui visionqa-target';
                            overlay.style.position = 'fixed';
                            overlay.style.zIndex = '3000000';
                            overlay.style.top = (rect.top) + 'px';
                            overlay.style.left = (rect.left) + 'px';
                            overlay.style.width = rect.width + 'px';
                            overlay.style.height = rect.height + 'px';
                            overlay.style.border = '10px solid #FFFF00';
                            overlay.style.boxShadow = '0 0 100px #FFFF00, inset 0 0 50px #FFFF00';
                            overlay.style.borderRadius = '12px';
                            overlay.style.pointerEvents = 'none';
                            overlay.style.transition = 'all 0.3s ease';

                            // 🎯 OK İŞARETİ (Elementin üstünde)
                            const arrow = document.createElement('div');
                            arrow.innerHTML = '⬇️ HEDEF BURASI! ⬇️';
                            arrow.style.position = 'absolute';
                            arrow.style.top = '-60px';
                            arrow.style.left = '50%';
                            arrow.style.transform = 'translateX(-50%)';
                            arrow.style.background = '#FFFF00';
                            arrow.style.color = '#000';
                            arrow.style.padding = '8px 15px';
                            arrow.style.fontWeight = '900';
                            arrow.style.fontSize = '18px';
                            arrow.style.borderRadius = '10px';
                            arrow.style.whiteSpace = 'nowrap';
                            arrow.style.boxShadow = '0 5px 15px rgba(0,0,0,0.5)';
                            overlay.appendChild(arrow);

                            document.body.appendChild(overlay);

                            // Parlama efekti
                            overlay.animate([
                                { opacity: 0.6, transform: 'scale(1)' },
                                { opacity: 1, transform: 'scale(1.1)' },
                                { opacity: 0.6, transform: 'scale(1)' }
                            ], { duration: 500, iterations: Infinity });
                            
                            // 3 saniye sonra sil ki kullanıcı görsün
                            setTimeout(() => { 
                                overlay.style.opacity = '0';
                                setTimeout(() => overlay.remove(), 300);
                            }, 3000);
                        }
                    }
                """, handle)
                await asyncio.sleep(3.0) # Tam 3 saniye boyunca donup bekler
        except:
            pass

    async def click_element(self, selector: str, timeout: int = 5000):
        """
        Elementi bul, NEON parlat ve tıkla. 
        🤖 SELF-HEALING: Eğer selector bulunamazsa AI'ya sor!
        """
        if not self.page: raise Exception("Sayfa yok!")
        
        try:
            # Önce normal yöntemle dene
            elm = self.page.locator(selector).first
            await elm.wait_for(timeout=timeout)
            await elm.scroll_into_view_if_needed()
            await self.highlight_element(elm)
            await elm.hover()
            await elm.click()
            print(f"✅ [WebExecutor] Tıklandı: {selector}")
            
        except Exception as e:
            print(f"⚠️ [Self-Healing] {selector} bulunamadı, AI moduna geçiliyor...")
            
            try:
                from core.models.llm_client import LLMClient
                llm = LLMClient()
                
                # 1. Mevcut ekranın görüntüsünü al
                screenshot = await self.screenshot()
                # 2. Sayfanın HTML yapısından ipucu al (sadece clickable elementler)
                page_data = await self.page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('button, a, input[type="submit"], [role="button"]'))
                        .map(el => el.innerText || el.getAttribute('aria-label') || el.value)
                        .filter(t => t && t.length > 1).join(', ')
                }""")
                
                # 3. AI'dan kök neden ve yeni konum iste
                analysis = await llm.analyze_error(
                    logs=f"Failed to find selector: {selector}. Visible elements: {page_data}",
                    screenshot_desc="Element not found. Screen layout captured."
                )
                
                # 4. Eğer AI yeni bir selector veya koordinat önerirse uygula
                new_sel = analysis.get("new_selector")
                if new_sel and new_sel != selector:
                    print(f"✨ [Self-Healing] AI yeni selector önerdi: {new_sel}")
                    elm = self.page.locator(new_sel).first
                    await elm.wait_for(timeout=3000)
                    await elm.click()
                    print(f"✅ [Self-Healing] Başarılı! {new_sel} kullanıldı.")
                    return

                # 5. Koordinat tabanlı tıklama (Visual fallback)
                print("🧠 [Self-Healing] Görsel analiz ile koordinat tahmini deneniyor...")
                # Basit bir brute-force: Buton metnine göre sayfa içinde ara (Playwright text search)
                text_match = selector.split("'")[-2] if "'" in selector else selector
                try:
                    await self.page.get_by_text(text_match, exact=False).first.click()
                    print(f"✅ [Self-Healing] Metin eşleşmesi ile tıklandı: {text_match}")
                except:
                    raise e # Hala başarısızsa orijinal hatayı fırlat
                    
            except Exception as final_e:
                print(f"❌ [Self-Healing] Başarısız: {str(final_e)}")
                raise e

    async def type_input(self, selector: str, text: str, delay_ms: int = 150):
        """Alanı bul, NEON parlat ve ağır çekim yaz."""
        if not self.page: raise Exception("Sayfa yok!")
        target = str(selector or "").lower()
        candidates = [("primary", self.page.locator(selector).first)]

        if any(k in target for k in ["email", "e-posta", "mail"]):
            candidates.extend([
                ("form-near-submit", self.page.locator("xpath=(//button[@type='submit']/ancestor::form//input[not(@type='hidden') and not(@disabled)])[1]").first),
                ("login-card-input", self.page.locator("xpath=(//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ', 'abcdefghijklmnopqrstuvwxyzçğiöşü'), 'giriş yap')]/ancestor-or-self::*[1]//input[not(@type='hidden') and not(@disabled)])[1]").first),
                ("label-email", self.page.get_by_label(re.compile(r"(e-?posta|email|mail)", re.I)).first),
                ("placeholder-email", self.page.get_by_placeholder(re.compile(r"(e-?posta|email|mail)", re.I)).first),
                ("name-email", self.page.locator("input[name*='email' i], input[id*='email' i]").first),
                ("autocomplete-email", self.page.locator("input[autocomplete='email'], input[autocomplete='username']").first),
                ("inputmode-email", self.page.locator("input[inputmode='email']").first),
                ("generic-input", self.page.locator("form input:not([type='hidden']):not([disabled]), input[type='text']:not([disabled])").first),
            ])
        elif any(k in target for k in ["password", "şifre", "sifre"]):
            candidates.extend([
                ("label-password", self.page.get_by_label(re.compile(r"(password|şifre|sifre)", re.I)).first),
                ("placeholder-password", self.page.get_by_placeholder(re.compile(r"(password|şifre|sifre)", re.I)).first),
                ("password-input", self.page.locator("input[type='password']").first),
                ("name-password", self.page.locator("input[name*='password' i], input[id*='password' i]").first),
            ])
        else:
            candidates.extend([
                ("generic-input", self.page.locator("form input:not([type='hidden']):not([disabled]), input[type='text']:not([disabled]), textarea:not([disabled])").first),
            ])

        last_error: Optional[Exception] = None
        for label, elm in candidates:
            try:
                await elm.wait_for(state="visible", timeout=2500)
                await elm.scroll_into_view_if_needed()
                await self.highlight_element(elm)
                await elm.click()
                await elm.fill(str(text))
                written = await elm.input_value()
                if str(written) != str(text):
                    await elm.fill("")
                    await self.page.keyboard.type(str(text), delay=delay_ms)
                    written = await elm.input_value()
                if str(written) == str(text):
                    print(f"✅ [WebExecutor] Yazıldı ({label}): {selector}")
                    return
            except Exception as e:
                last_error = e
                continue

        raise last_error if last_error else Exception(f"type failed: {selector}")

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
