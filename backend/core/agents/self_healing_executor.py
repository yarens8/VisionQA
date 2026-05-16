
import os
import tempfile
import asyncio
from typing import Dict, Any, Optional, List
from executors.web.web_executor import WebExecutor
from core.models.llm_client import LLMClient
from core.models.vision_provider import VisionProviderManager
from core.agents.intelligence_vault import IntelligenceVault

class SelfHealingExecutor:
    """
    💪 VisionQA — Kendi Kendini Onaran Test Yürütücü (Self-Healing Executor)
    """

    def __init__(self, web_executor: WebExecutor, vault_data: Optional[Dict[str, Any]] = None):
        self.web = web_executor
        self.llm = LLMClient()
        self.vision = VisionProviderManager()
        self.ai_healing_enabled = os.getenv("EXECUTION_AI_HEALING_ENABLED", "false").lower() == "true"
        self.vision_obstacles_enabled = os.getenv("EXECUTION_VISION_OBSTACLES_ENABLED", "false").lower() == "true"
        self.vault = IntelligenceVault(vault_data)
        self.last_healing_report = None

    # ═══════════════════════════════════════════════════════════════
    #  ANA İŞLEMLER (Safe Actions)
    # ═══════════════════════════════════════════════════════════════

    async def navigate(self, url: str):
        """URL'e git ve global engelleri temizle."""
        await self.web.navigate(url)
        # Sayfa açılır açılmaz beliren engelleri (cookie banner vs) temizle
        await self.handle_global_obstacles()

    async def click(self, selector: str):
        """Güvenli tıklama — element bulunamazsa iyileştirmeyi dene."""
        try:
            await self.web.click_element(selector)
        except Exception as e:
            if not self.ai_healing_enabled:
                raise e
            print(f"⚠️ [Self-Healing] Tıklama başarısız: {selector}. İyileştirme başlatılıyor...")
            success = await self.heal_and_retry("click", selector, str(e))
            if not success:
                raise e

    async def type(self, selector: str, text: str):
        """Güvenli yazma — element bulunamazsa iyileştirmeyi dene."""
        try:
            await self.web.type_input(selector, text)
        except Exception as e:
            if not self.ai_healing_enabled:
                raise e
            print(f"⚠️ [Self-Healing] Yazma başarısız: {selector}. İyileştirme başlatılıyor...")
            success = await self.heal_and_retry("type", selector, str(e), value=text)
            if not success:
                raise e

    async def verify(self, selector: str) -> bool:
        """Güvenli doğrulama — element görünmezse iyileştirmeyi dene."""
        is_visible = await self.web.verify_element(selector)
        if not is_visible:
            if not self.ai_healing_enabled:
                return False
            print(f"⚠️ [Self-Healing] Doğrulama başarısız: {selector}. İyileştirme başlatılıyor...")
            success = await self.heal_and_retry("verify", selector, "Element not visible")
            return success
        return True

    # ═══════════════════════════════════════════════════════════════
    #  İYİLEŞTİRME VE TEMİZLEME MANTIĞI
    # ═══════════════════════════════════════════════════════════════

    async def handle_global_obstacles(self):
        """
        🍪 Global Engel Çözücü (Global Solvers)
        Çerez banner'ları ve 'Kadın/Erkek' seçimi gibi onboarding engellerini temizler.
        """
        print("🧹 [Global Solvers] Sayfa engellerden temizleniyor...")
        
        # 🟢 1. QUICK FIX: Kullanıcının tercihine göre onboarding aşma
        try:
            user_gender = self.vault.get_value("gender").upper() # 'KADIN' veya 'ERKEK'
            btn = self.web.page.get_by_text(user_gender, exact=False).first
            if await btn.is_visible():
                print(f"✨ [Vault Solver] Profil tercihi ({user_gender}) bulundu, seçiliyor...")
                # 🔴 BUTONU PARLAT (Kullanıcı hangisinin seçildiğini görsün)
                await self.web.highlight_element(btn)
                await btn.click()
                await asyncio.sleep(1)
        except:
            pass

        # Bekleme ve Fallback (Kapat/Kabul Et gibi)
        await asyncio.sleep(1)

        if not self.vision_obstacles_enabled:
            print("ℹ️ [Global Solvers] Vision obstacle taraması kapalı; hızlı DOM/selector akışıyla devam.")
            return

        # 🔵 2. GORSEL COZUM: optional vision provider ile tespit
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            screenshot_path = tmp.name
        
        try:
            await self.web.screenshot(screenshot_path)
            elements, provider = await self.vision.detect_obstacles(screenshot_path)
            
            for elem in elements:
                if elem.get("score", 0) > 0.40:
                    label = elem["label"].lower()
                    # Sadece kapatma/kabul değil, 'kadın/erkek' gibi seçimleri de engel sayıyoruz
                    targets = ["accept", "dismiss", "close", "agree", "ok", "allow", "kadın", "erkek", "woman", "man"]
                    if any(t in label for t in targets):
                        print(f"✨ [Global Solver] Engel/Seçim tespit edildi: {label} ({provider}, Score: {elem['score']:.2f})")
                        box = elem["box"]
                        if isinstance(box, dict):
                            x = (box["xmin"] + box["xmax"]) / 2
                            y = (box["ymin"] + box["ymax"]) / 2
                            await self.web.page.mouse.click(x, y)
                        elif isinstance(box, list) and len(box) == 4:
                            x = (box[0] + box[2]) / 2
                            y = (box[1] + box[3]) / 2
                            await self.web.page.mouse.click(x, y)
                        
                        await asyncio.sleep(1)
        except Exception as e:
            print(f"⚠️ [Global Solver] AI ile engel temizlenirken hata: {e}")
        finally:
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)

    async def heal_and_retry(self, action_type: str, selector: str, error_msg: str, value: str = "") -> bool:
        """
        🚑 İyileştirme Süreci (Healing Phase)
        """
        if not self.ai_healing_enabled:
            return False
        print(f"🚑 [Healing] Analiz ediliyor: {action_type} -> {selector}")
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            screenshot_path = tmp.name
        
        try:
            await self.web.screenshot(screenshot_path)
            
            # 1. Vision provider world view al
            world_view, _provider = await self.vision.get_world_view(screenshot_path)
            
            # 2. LLM Analizi
            analysis = await self.llm.analyze_error(
                logs=f"Action: {action_type}\nOriginal Selector: {selector}\nError: {error_msg}",
                screenshot_desc=world_view
            )
            
            # Kullanıcıya yönelik detaylı açıklama oluşturma
            root_cause = analysis.get("root_cause", "Bilinmeyen engel")
            suggestion = analysis.get("suggestion", "Görsel onarım denendi")
            
            analysis["human_explanation"] = f"Hata Nedeni: {root_cause}. VisionQA Çözümü: {suggestion}."
            
            self.last_healing_report = analysis
            action = analysis.get("self_healing_action", "none")
            new_selector = analysis.get("new_selector")
            
            print(f"🔍 [Healing Analysis] Neden: {root_cause} | Öneri: {action}")
            
            # 3. İyileştirme Aksiyonlarını Uygula
            if action == "dismiss_overlay":
                await self.handle_global_obstacles()
            elif action == "wait_longer":
                await asyncio.sleep(3)
            elif action == "scroll_to_element":
                try:
                    await self.web.page.locator(selector).first.scroll_into_view_if_needed()
                except:
                    pass

            # 4. RETRY
            retry_selector = new_selector if (action == "retry_with_new_selector" and new_selector) else selector
            
            try:
                if action_type == "click":
                    await self.web.click_element(retry_selector)
                elif action_type == "type":
                    await self.web.type_input(retry_selector, value)
                elif action_type == "verify":
                    return await self.web.verify_element(retry_selector)
                
                print(f"🎉 [Healing] BAŞARILI! Test '{retry_selector}' kullanılarak kurtarıldı.")
                return True
            except Exception as e:
                print(f"❌ [Healing] İyileştirme denemesi başarısız: {e}")
                return False
                
        finally:
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)
