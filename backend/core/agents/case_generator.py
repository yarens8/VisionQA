
import os
import json
import re
import base64
import tempfile
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests

load_dotenv()


class AICaseGenerator:
    """
    🤖 Otonom Test Mimarı (Autonomous Test Architect)

    Akış:
    1. URL al
    2. WebExecutor ile sayfayı aç ve screenshot al  (Eller)
    3. Grounding DINO ile screenshot'taki UI elementlerini tespit et  (Gözler)
    4. Groq + Llama 3.3 70B ile test senaryoları üret  (Beyin)
    5. Happy Path + Negative + Edge Case + Security senaryolarını döndür

    Kullanım:
        generator = AICaseGenerator()
        cases = await generator.generate_cases_from_url("https://saucedemo.com")
    """

    def __init__(self):
        from core.models.llm_client import LLMClient
        self.llm = LLMClient()
        self._dinox = None  # Lazy: sadece use_screenshot=True olduğunda yüklenir
        print("✅ [AICaseGenerator] LLM (Groq) hazır. DINO ekran analizi için bekleniyor.")

    def _get_dinox(self):
        """Grounding DINO istemcisini ihtiyaç duyulduğunda başlatır."""
        if self._dinox is None:
            from core.models.dinox_client import DINOXClient
            self._dinox = DINOXClient()
        return self._dinox


    # ─────────────────────────────────────────────
    # ANA METOD: URL → Test Cases
    # ─────────────────────────────────────────────

    async def generate_cases_from_url(
        self,
        url: str,
        platform: str = "web",
        use_screenshot: bool = True,
        strict_visual: bool = False,
        require_live_show: bool = False
    ) -> List[Dict[str, Any]]:
        """
        URL'den otonom olarak test senaryoları üretir.

        Args:
            url:            Test edilecek sayfa URL'si
            platform:       "web" | "mobile" | "api"
            use_screenshot: True → Gerçek sayfa analizi (Grounding DINO)
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

        # ADIM 1: Görsel ve Yapısal Analiz (Eyes: Grounding DINO)
        page_analysis = await self._analyze_page(
            url=url,
            use_screenshot=use_screenshot,
            strict_visual=strict_visual,
            require_live_show=require_live_show
        )

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
    # ADIM 1: Sayfa Analizi (Grounding DINO + Screenshot)
    # ─────────────────────────────────────────────

    async def _analyze_page(
        self,
        url: str,
        use_screenshot: bool,
        strict_visual: bool = False,
        require_live_show: bool = False
    ) -> str:
        """
        Sayfayı analiz eder, UI elementlerini çizer ve metin olarak döndürür.
        """
        if not use_screenshot:
            return self._infer_context_from_url(url)

        screenshot_path = None
        executor = None
        try:
            from executors.web.web_executor import WebExecutor
            import tempfile
            import os
            import json

            # Backend kendi sessiz işine (Headless) devam eder
            executor = WebExecutor(headless=True)
            await executor.start()
            await executor.navigate(url)
            source_viewport = {"width": 1280, "height": 720}
            if getattr(executor, "page", None) and executor.page.viewport_size:
                source_viewport = executor.page.viewport_size

            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            screenshot_path = tmp.name
            tmp.close()

            # DINO için full-page yerine viewport screenshot kullanıyoruz.
            # Bu, canlı şovdaki kutu koordinat kaymalarını ciddi şekilde azaltır.
            await executor.screenshot(screenshot_path, full_page=False)
            
            # DINO analiz
            elements = await self._get_dinox().detect_elements(screenshot_path)

            # --- CANLI ŞOV: DINO sonuçlarıyla birlikte Bridge'e gönder ---
            try:
                print(f"🚦 [AI] Kullanıcının ekranında CANLI ŞOV başlatılıyor... ({url})")
                bridge_payload = {
                    "url": url,
                    "elements": elements if elements else [],
                    "source_viewport": source_viewport,
                    "wait_for_completion": True
                }

                # Backend bazen host'ta, bazen container içinde çalışır.
                # Bu yüzden bridge için birden fazla adres deneriz.
                configured_bridge = os.getenv("DESKTOP_BRIDGE_URL", "").strip()
                bridge_candidates = []
                if configured_bridge:
                    bridge_candidates.append(configured_bridge.rstrip("/"))
                bridge_candidates.extend([
                    "http://127.0.0.1:8001",
                    "http://localhost:8001",
                    "http://host.docker.internal:8001",
                ])

                sent = False
                last_bridge_error = None
                for bridge_base in dict.fromkeys(bridge_candidates):
                    launch_url = f"{bridge_base}/launch-vision"
                    try:
                        # connect timeout kısa, read timeout uzun: canlı şov bitene kadar bekleyebilir.
                        response = requests.post(
                            launch_url,
                            json=bridge_payload,
                            timeout=(3, 900)
                        )
                        response.raise_for_status()
                        print(
                            f"✅ [AI] Bridge'e {len(elements) if elements else 0} element gönderildi! "
                            f"({bridge_base})"
                        )
                        sent = True
                        break
                    except Exception as bridge_err:
                        last_bridge_error = bridge_err
                        print(f"⚠️ [AI] Bridge denemesi başarısız ({bridge_base}): {bridge_err}")

                if not sent:
                    raise RuntimeError(last_bridge_error or "Desktop Bridge endpointlerine bağlanılamadı.")
                # Bridge senkron modda tamamlanana kadar beklediği için ekstra bekleme gerekmez.
            except Exception as e:
                print(f"⚠️ [AI] Köprüye ulaşılamadı: {e}")
                if require_live_show:
                    raise RuntimeError(f"Desktop Bridge çalışmıyor: {e}") from e
            # ----------------------------------------------------------------

            context = self._build_world_view(url, elements, use_url_inference_fallback=False)
            if strict_visual and "No UI elements detected visually." in context:
                raise RuntimeError("Görsel analiz tamamlandı ancak DINO hiçbir UI elementi tespit edemedi.")
            return context

        except Exception as e:
            if strict_visual:
                raise RuntimeError(f"Görsel analiz başarısız: {e}") from e
            print(f"⚠️ [Analiz] Hata: {e}. URL'den çıkarım yapılıyor.")
            return self._infer_context_from_url(url)
        finally:
            if executor is not None:
                try:
                    await executor.stop()
                except Exception:
                    pass
            if screenshot_path:
                try:
                    os.remove(screenshot_path)
                except Exception:
                    pass

    def _build_world_view(
        self,
        url: str,
        elements: List[Dict],
        use_url_inference_fallback: bool = True
    ) -> str:
        """
        Grounding DINO çıktısını LLM için okunabilir bağlama çevirir.
        """
        lines = [f"URL: {url}", "### VISUAL WORLD VIEW (Detected via Grounding DINO)"]
        
        if not elements:
            lines.append("\nNo UI elements detected visually.")
            if use_url_inference_fallback:
                lines.append("Using URL-based inference as fallback.")
                lines.append(self._infer_context_from_url(url))
            return "\n".join(lines)

        lines.append(f"\nDetected {len(elements)} UI elements:")
        for i, elem in enumerate(elements, 1):
            label = elem.get("label", "unknown")
            score = elem.get("score", 0)
            box = elem.get("box", [])
            lines.append(f"  {i}. {label.upper()}: position={box}, confidence={score:.2f}")

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

        # LLM kategori anahtarlarını daha esnek normalize et
        category_map = {
            "happy_path": "happy_path",
            "happy": "happy_path",
            "positive": "happy_path",
            "negative_path": "negative_path",
            "negative": "negative_path",
            "edge_cases": "edge_case",
            "edge_case": "edge_case",
            "edge": "edge_case",
            "security_checks": "security",
            "security": "security",
            "security_check": "security",
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
            "edge_case": "medium",
            "security_checks": "critical"
        }

        def normalize_category(raw_key: str) -> str:
            k = str(raw_key or "").strip().lower()
            return category_map.get(k, "happy_path")

        for category_key, scenarios in raw_cases.items():
            # Meta alanları atla (page_analysis_summary, total_rules_covered vb.)
            if not isinstance(scenarios, list):
                continue
            normalized_category = normalize_category(category_key)

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
                # LLM çıktısını mümkün olduğunca aynen taşımak için,
                # boş/uyumsuz step alanlarını minimum normalize ediyoruz.
                # (agresif "enrich/override" burada uygulanmıyor)
                if not formatted_steps:
                    formatted_steps = [{
                        "order": 1,
                        "action": "navigate",
                        "target": url,
                        "value": "",
                        "expected": "Page opens successfully"
                    }]

                # Priority: Önce LLM'in risk_level'ını kullan, yoksa kategori fallback
                llm_risk = scenario.get("risk_level", "").lower()
                priority = risk_to_priority.get(llm_risk, fallback_priority.get(normalized_category, "medium"))

                case_data = {
                    "title": scenario.get("title", f"Test Case {len(cases) + 1}"),
                    "description": scenario.get("expected_outcome", scenario.get("expected", scenario.get("description", ""))),
                    "category": normalized_category,
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

    def _enrich_steps_for_case(
        self,
        formatted_steps: List[Dict[str, Any]],
        scenario: Dict[str, Any],
        category_key: str
    ) -> List[Dict[str, Any]]:
        """
        LLM'in döndürdüğü şablon adımları daha çalıştırılabilir ve birbirinden ayrışır hale getirir.
        """
        title = str(scenario.get("title", "")).lower()
        enriched = []
        is_invalid_email_case = (
            category_key == "negative_path"
            and ("invalid" in title and ("email" in title or "mail" in title))
        )
        for s in formatted_steps:
            step = dict(s)
            action = str(step.get("action", "")).lower()
            target = str(step.get("target", ""))
            value = str(step.get("value", ""))
            t = target.lower()

            # İngilizce sabit placeholder/selectors'ı daha genel hale getir
            if action == "type":
                if "placeholder='email'" in t or "placeholder=\"email\"" in t:
                    step["target"] = "input[type='email']"
                elif "placeholder='password'" in t or "placeholder=\"password\"" in t:
                    step["target"] = "input[type='password']"

            if action == "click":
                if "has-text('submit')" in t or 'has-text("submit")' in t:
                    step["target"] = "button[type='submit']"
                # Login sayfalarında submit benzeri butonları normalize et
                if any(k in t for k in ["devam et", "giriş yap", "giris yap", "continue", "login"]):
                    step["target"] = "button[type='submit']"

            # Negatif/edge/security senaryolarda value'yu daha belirgin yap
            if action == "type" and not value.strip():
                if "email" in t or "mail" in t:
                    if "invalid" in title or "format" in title or category_key == "negative_path":
                        step["value"] = "invalid-email-format"
                    elif "empty" in title:
                        step["value"] = ""
                    else:
                        step["value"] = "user@example.com"
                elif "password" in t or "şifre" in t or "sifre" in t:
                    if "short" in title or "length" in title:
                        step["value"] = "123"
                    elif "empty" in title:
                        step["value"] = ""
                    elif "sql" in title or "injection" in title:
                        step["value"] = "' OR 1=1 --"
                    else:
                        step["value"] = "ValidPass123!"
                elif "sql" in title or "injection" in title:
                    step["value"] = "' OR 1=1 --"
                elif "xss" in title:
                    step["value"] = "<script>alert('xss')</script>"

            enriched.append(step)

        # Invalid email senaryosunda password typing adımını çıkar:
        # Beklenen akış: email yaz -> submit/devam -> hata doğrula
        if is_invalid_email_case:
            filtered = []
            for e in enriched:
                if str(e.get("action", "")).lower() == "type":
                    tt = str(e.get("target", "")).lower()
                    if "password" in tt or "şifre" in tt or "sifre" in tt:
                        continue
                filtered.append(e)
            enriched = filtered

            has_submit_click = any(
                str(e.get("action", "")).lower() == "click"
                and ("submit" in str(e.get("target", "")).lower() or "devam" in str(e.get("target", "")).lower())
                for e in enriched
            )
            if not has_submit_click:
                enriched.append({
                    "order": len(enriched) + 1,
                    "action": "click",
                    "target": "button[type='submit']",
                    "value": "",
                    "expected": "Form submit attempt edilir"
                })

            has_verify = any(str(e.get("action", "")).lower() == "verify" for e in enriched)
            if not has_verify:
                enriched.append({
                    "order": len(enriched) + 1,
                    "action": "verify",
                    "target": ".error, .error-message, .alert, [role='alert']",
                    "value": "",
                    "expected": "Geçersiz email için hata mesajı görünür"
                })

            # order alanlarını yeniden sırala
            for idx, e in enumerate(enriched, start=1):
                e["order"] = idx

        # Aynı aksiyon/target pattern'i tekrar ediyorsa verify adımını güçlendir
        actions_targets = [(e.get("action"), e.get("target")) for e in enriched]
        if len(actions_targets) == len(set(actions_targets)):
            return enriched

        for e in enriched:
            if str(e.get("action", "")).lower() == "verify" and str(e.get("target", "")).strip() in [".error-message", ".error"]:
                e["target"] = ".error, .error-message, .alert, [role='alert']"
        return enriched

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
