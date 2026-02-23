
import os
import json
import re
import base64
import tempfile
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class AICaseGenerator:
    """
    🤖 Otonom Test Mimarı (Autonomous Test Architect)

    Akış:
    1. URL al
    2. WebExecutor ile sayfayı aç ve screenshot al  (Eller)
    3. SAM3/DINO-X ile screenshot'taki UI elementlerini tespit et  (Gözler)
    4. Groq + Llama 3.3 70B ile test senaryoları üret  (Beyin)
    5. Happy Path + Negative + Edge Case + Security senaryolarını döndür

    Kullanım:
        generator = AICaseGenerator()
        cases = await generator.generate_cases_from_url("https://saucedemo.com")
    """

    def __init__(self):
        from core.models.llm_client import LLMClient
        from core.models.sam3_client import SAM3Client
        from core.models.dinox_client import DINOXClient
        self.llm = LLMClient()
        self.sam = SAM3Client()
        self.dinox = DINOXClient()
        print("✅ [AICaseGenerator] LLM + SAM3 + DINO-X (Gözler) hazır.")

    # ─────────────────────────────────────────────
    # ANA METOD: URL → Test Cases
    # ─────────────────────────────────────────────

    async def generate_cases_from_url(
        self,
        url: str,
        platform: str = "web",
        use_screenshot: bool = True
    ) -> List[Dict[str, Any]]:
        """
        URL'den otonom olarak test senaryoları üretir.

        Args:
            url:            Test edilecek sayfa URL'si
            platform:       "web" | "mobile" | "api"
            use_screenshot: True → Gerçek sayfa analizi (SAM3)
                            False → Sadece LLM tahmini (hızlı)
        Returns:
            [
                {
                    "title": "...",
                    "description": "...",
                    "category": "happy_path|negative|edge_case|security",
                    "priority": "high|medium|low",
                    "steps": [{"order": 1, "action": "click", "target": "...", "expected": "..."}]
                }, ...
            ]
        """
        print(f"\n{'='*60}")
        print(f"🧠 [AICaseGenerator] Analiz Başlıyor: {url}")
        print(f"{'='*60}")

        # ADIM 1: Görsel ve Yapısal Analiz (Eyes: SAM3 + DINO-X)
        page_analysis = await self._analyze_page(url, use_screenshot)

        # ADIM 2: Sayfayı Anlamlandırma (Identity Phase)
        # LLM'e sayfadaki elementleri ve URL'i verip sitenin amacını ve akışını çözdürürüz.
        page_identity = await self.llm.identify_page_purpose(url, page_analysis)
        print(f"🆔 [Page Identity] Bu sayfa: {page_identity.get('page_type', 'Bilinmiyor')}")
        print(f"🏢 [Business Rules] Tespit edilen kurallar: {len(page_identity.get('business_rules', []))}")

        # ADIM 3: Akıllı Senaryolar Üretme (Brain Phase)
        # Sayfanın kimliğine göre (örn: Sipariş ekranı) mantıksal testler üretilir.
        raw_cases = await self.llm.generate_test_cases(
            url=url,
            page_context=page_analysis,
            page_identity=page_identity, # Kimlik raporunu buraya geçiyoruz
            platform=platform
        )

        # ADIM 4: Sonuçları Standart Formata Çevir
        cases = self._format_cases(raw_cases, url)

        print(f"\n✅ [AICaseGenerator] Toplam {len(cases)} test senaryosu üretildi!")
        print(f"   → Happy Path: {sum(1 for c in cases if c['category'] == 'happy_path')}")
        print(f"   → Negative:   {sum(1 for c in cases if c['category'] == 'negative_path')}")
        print(f"   → Edge Case:  {sum(1 for c in cases if c['category'] == 'edge_case')}")
        print(f"   → Security:   {sum(1 for c in cases if c['category'] == 'security')}")

        return cases

    # ─────────────────────────────────────────────
    # ADIM 1: Sayfa Analizi (SAM3 + Screenshot)
    # ─────────────────────────────────────────────

    async def _analyze_page(self, url: str, use_screenshot: bool) -> str:
        """
        Sayfayı analiz eder ve UI elementlerini metin olarak döndürür.
        SAM3 başarısız olursa URL'den çıkarım yapar.
        """
        if not use_screenshot:
            return self._infer_context_from_url(url)

        try:
            # Screenshot al
            screenshot_path = await self._take_screenshot(url)

            if screenshot_path:
                # 1. SAM3 (Görsel Segmentasyon) - Piksel Hassasiyeti
                sam_elements = self.sam.detect_ui_elements(screenshot_path, platform="web")
                
                # 2. DINO-X (Semantik Tanımlama) - Anlamsal Etiketleme
                dinox_elements = await self.dinox.detect_elements(screenshot_path)
                
                # 3. Unified World View (Birleşik Dünya Görüşü)
                context = self._build_unified_world_view(url, sam_elements, dinox_elements)
                
                print(f"👁️ [World View] SAM3: {len(sam_elements)} | DINO-X: {len(dinox_elements)} element birleştirildi.")
                return context
            else:
                print("⚠️ [Screenshot] Alınamadı, URL'den çıkarım yapılıyor.")
                return self._infer_context_from_url(url)

        except Exception as e:
            print(f"⚠️ [Analiz] Hata: {e}. URL'den çıkarım yapılıyor.")
            return self._infer_context_from_url(url)

    async def _take_screenshot(self, url: str) -> Optional[str]:
        """Playwright ile sayfanın screenshot'ını alır."""
        try:
            from executors.web.web_executor import WebExecutor
            executor = WebExecutor(headless=True)
            await executor.start()
            await executor.navigate(url)

            # Temp dosyaya kaydet
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            screenshot_path = tmp.name
            tmp.close()

            await executor.screenshot(screenshot_path)
            await executor.stop()

            print(f"📸 [Screenshot] Alındı: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            print(f"⚠️ [Screenshot] Playwright hatası: {e}")
            return None

    def _build_unified_world_view(self, url: str, sam_elements: List[Dict], dinox_elements: List[Dict]) -> str:
        """
        SAM3 ve DINO-X verilerini tek bir anlamlı bağlamda birleştirir.
        """
        lines = [f"URL: {url}", "### UNIFIED WORLD VIEW (Visual + Semantic Analysis)"]
        
        # Önce DINO-X (Semantik Etiketler) - LLM için en değerli bilgi
        lines.append("\nSemantic Elements (What they MEAN):")
        for i, elem in enumerate(dinox_elements, 1):
            label = elem.get("label", "unknown")
            score = elem.get("score", 0)
            box = elem.get("box", [])
            lines.append(f"  {i}. {label.upper()}: position={box}, confidence={score:.2f}")

        # Sonra SAM3 (Piksel Segmentleri) - Geometrik Bilgi
        lines.append("\nVisual Segments (Exact Boundaries):")
        for i, elem in enumerate(sam_elements, 1):
            label = elem.get("label", "unknown")
            box = elem.get("box", [])
            lines.append(f"  - Segment {i} ({label}): {box}")

        return "\n".join(lines)

    def _elements_to_context(self, elements: List[Dict], url: str) -> str:
        """(Legacy) SAM3 element listesini LLM için okunabilir metne çevirir."""
        if not elements:
            return self._infer_context_from_url(url)

        lines = [f"URL: {url}", "Detected UI Elements:"]
        for elem in elements:
            label = elem.get("label", "unknown")
            score = elem.get("score", 0)
            box = elem.get("box", [])
            lines.append(f"  - {label} (confidence: {score:.2f}, position: {box})")

        return "\n".join(lines)

    def _infer_context_from_url(self, url: str) -> str:
        """
        URL'e bakarak sayfa içeriğini tahmin eder.
        Screenshot alınamadığında fallback olarak kullanılır.
        """
        url_lower = url.lower()
        context_parts = [f"URL: {url}"]

        # URL'den sayfa tipini çıkar
        if any(k in url_lower for k in ["login", "signin", "auth"]):
            context_parts.append("Page Type: Login/Authentication Page")
            context_parts.append("Expected Elements: username field, password field, login button, forgot password link")
        elif any(k in url_lower for k in ["register", "signup", "kayit"]):
            context_parts.append("Page Type: Registration Page")
            context_parts.append("Expected Elements: name, email, password, confirm password fields, register button")
        elif any(k in url_lower for k in ["cart", "sepet", "basket"]):
            context_parts.append("Page Type: Shopping Cart")
            context_parts.append("Expected Elements: product list, quantity input, remove button, checkout button, total price")
        elif any(k in url_lower for k in ["checkout", "payment", "odeme"]):
            context_parts.append("Page Type: Checkout/Payment Page")
            context_parts.append("Expected Elements: address form, payment fields, credit card input, order button")
        elif any(k in url_lower for k in ["search", "arama"]):
            context_parts.append("Page Type: Search Results Page")
            context_parts.append("Expected Elements: search bar, filter options, product cards, pagination")
        elif any(k in url_lower for k in ["product", "urun", "item"]):
            context_parts.append("Page Type: Product Detail Page")
            context_parts.append("Expected Elements: product image, title, price, add to cart button, quantity selector")
        elif any(k in url_lower for k in ["dashboard", "panel", "admin"]):
            context_parts.append("Page Type: Dashboard/Admin Panel")
            context_parts.append("Expected Elements: navigation menu, statistics cards, data tables, action buttons")
        elif any(k in url_lower for k in ["profile", "account", "hesap"]):
            context_parts.append("Page Type: User Profile/Account Page")
            context_parts.append("Expected Elements: profile form, avatar, save button, password change section")
        else:
            context_parts.append("Page Type: General Web Application")
            context_parts.append("Expected Elements: navigation, content area, forms, buttons, links")

        return "\n".join(context_parts)

    # ─────────────────────────────────────────────
    # ADIM 3: Sonuçları Standart Formata Çevir
    # ─────────────────────────────────────────────

    def _format_cases(self, raw_cases: Dict[str, Any], url: str) -> List[Dict[str, Any]]:
        """
        LLM'den gelen ham JSON'ı veritabanına kaydedilebilir formata çevirir.

        Yeni Mimari:
          - priority artık LLM'in risk_level çıktısından alınır (sabit map yerine)
          - covers_rule, violation_strategy, expected_outcome gibi zengin alanlar dahil edilir
          - page_analysis_summary, total_rules_covered gibi meta alanlar atlanır
        """
        cases = []

        # LLM çıktısındaki kategori anahtarları → iç kategori isimlerimiz
        category_map = {
            "happy_path": "happy_path",
            "negative_path": "negative_path",
            "edge_cases": "edge_case",
            "security_checks": "security"
        }

        # risk_level → priority dönüşümü (LLM'in verdiği risk seviyesinden)
        risk_to_priority = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low"
        }

        # Varsayılan priority (LLM risk_level vermezse kategori bazlı fallback)
        fallback_priority = {
            "happy_path": "high",
            "negative_path": "high",
            "edge_cases": "medium",
            "security_checks": "critical"
        }

        for category_key, scenarios in raw_cases.items():
            # Meta alanları atla (page_analysis_summary, total_rules_covered vb.)
            if not isinstance(scenarios, list):
                continue
            # Bilinmeyen kategori anahtarlarını atla
            if category_key not in category_map:
                continue

            for scenario in scenarios:
                if not isinstance(scenario, dict):
                    continue

                steps = scenario.get("steps", [])
                formatted_steps = []

                for i, step in enumerate(steps):
                    if isinstance(step, str):
                        formatted_steps.append({
                            "order": i + 1,
                            "action": self._infer_action(step),
                            "target": step,
                            "value": "",
                            "expected": scenario.get("expected_outcome", "Step completes successfully")
                        })
                    elif isinstance(step, dict):
                        formatted_steps.append({
                            "order": step.get("order", i + 1),
                            "action": step.get("action", "interact"),
                            "target": step.get("target", step.get("description", "")),
                            "value": step.get("value", ""),
                            "expected": step.get("expected", "Step completes successfully")
                        })

                # Priority: Önce LLM'in risk_level'ını kullan, yoksa kategori fallback
                llm_risk = scenario.get("risk_level", "").lower()
                priority = risk_to_priority.get(llm_risk, fallback_priority.get(category_key, "medium"))

                case_data = {
                    "title": scenario.get("title", f"Test Case {len(cases) + 1}"),
                    "description": scenario.get("expected_outcome", scenario.get("expected", scenario.get("description", ""))),
                    "category": category_map.get(category_key, category_key),
                    "priority": priority,
                    "source_url": url,
                    "steps": formatted_steps
                }

                # Zengin meta verileri ekle (varsa)
                if scenario.get("covers_rule"):
                    case_data["covers_rule"] = scenario["covers_rule"]
                if scenario.get("violation_strategy"):
                    case_data["violation_strategy"] = scenario["violation_strategy"]

                cases.append(case_data)

        return cases

    def _infer_action(self, step_text: str) -> str:
        """Adım metninden aksiyon türünü çıkarır."""
        step_lower = step_text.lower()
        if any(k in step_lower for k in ["click", "press", "tap", "tıkla"]):
            return "click"
        elif any(k in step_lower for k in ["type", "enter", "input", "write", "yaz", "gir"]):
            return "type"
        elif any(k in step_lower for k in ["navigate", "go to", "open", "git", "aç"]):
            return "navigate"
        elif any(k in step_lower for k in ["verify", "check", "assert", "doğrula", "kontrol"]):
            return "verify"
        elif any(k in step_lower for k in ["wait", "bekle"]):
            return "wait"
        elif any(k in step_lower for k in ["scroll", "kaydır"]):
            return "scroll"
        else:
            return "interact"

    # ─────────────────────────────────────────────
    # YARDIMCI: Açıklamadan Adım Üret
    # ─────────────────────────────────────────────

    async def generate_cases_from_description(
        self,
        description: str,
        url: str = "",
        platform: str = "web"
    ) -> List[Dict[str, Any]]:
        """
        Kullanıcının yazdığı açıklamadan test case üretir.
        Örn: "Login ol ve sepete ürün ekle"
        """
        print(f"🧠 [AICaseGenerator] Açıklamadan üretiliyor: {description}")

        context = f"URL: {url}\nUser Story: {description}"
        raw_cases = await self.llm.generate_test_cases(
            url=url or "application",
            page_context=context,
            platform=platform
        )

        return self._format_cases(raw_cases, url)
