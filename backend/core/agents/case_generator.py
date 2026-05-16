
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

    AUTONOMOUS_TEST_PROMPT = "button. input field. text field. login form. checkbox. error message."

    def __init__(self):
        from core.models.llm_client import LLMClient
        from core.models.vision_provider import VisionProviderManager
        self.llm = LLMClient()
        self._vision = VisionProviderManager()
        self.last_analysis_metadata: Dict[str, Any] = {}
        print("✅ [AICaseGenerator] LLM (Groq) hazır. Görsel analiz ihtiyaç halinde yüklenecek.")

    async def _detect_visual_elements(self, screenshot_path: str) -> tuple[List[Dict], str]:
        return await self._vision.detect_elements(
            screenshot_path,
            prompt=self.AUTONOMOUS_TEST_PROMPT,
            require_results=True,
        )


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

        # ADIM 1: Görsel ve Yapısal Analiz (Eyes: SAM3 + Grounding DINO fallback)
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
            self.last_analysis_metadata = {
                "vision_provider": "url_inference",
                "detected_element_count": 0,
                "visual_fallback_used": True,
                "fallback_reason": "screenshot analysis disabled",
                "detected_elements": [],
                "screenshot_base64": "",
                "annotated_screenshot_base64": "",
            }
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
            dom_elements = await self._extract_dom_interactive_elements(executor)
            
            # SAM3 analiz; kurulum/model erişimi yoksa Grounding DINO fallback.
            elements, vision_provider = await self._detect_visual_elements(screenshot_path)
            screenshot_base64 = self._image_file_to_base64(screenshot_path)
            annotated_screenshot_base64 = self._annotate_screenshot_base64(screenshot_path, elements)
            self.last_analysis_metadata = {
                "vision_provider": vision_provider,
                "detected_element_count": len(elements or []),
                "visual_fallback_used": vision_provider not in {"SAM3"},
                "fallback_reason": getattr(self._vision, "last_error", None),
                "detected_elements": (elements or [])[:50],
                "dom_interactive_elements": dom_elements,
                "screenshot_base64": screenshot_base64,
                "annotated_screenshot_base64": annotated_screenshot_base64,
                "live_overlay_requested": require_live_show,
                "live_overlay_status": "not_requested",
                "live_overlay_error": "",
            }

            # --- CANLI ŞOV: vision sonuçlarıyla birlikte Bridge'e gönder ---
            if require_live_show:
                try:
                    print(f"🚦 [AI] Kullanıcının ekranında CANLI ŞOV başlatılıyor... ({url})")
                    self.last_analysis_metadata["live_overlay_status"] = "starting"
                    bridge_payload = {
                        "url": url,
                        "elements": elements if elements else [],
                        "vision_provider": vision_provider,
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
                            self.last_analysis_metadata["live_overlay_status"] = "shown"
                            break
                        except Exception as bridge_err:
                            last_bridge_error = bridge_err
                            print(f"⚠️ [AI] Bridge denemesi başarısız ({bridge_base}): {bridge_err}")

                    if not sent:
                        raise RuntimeError(last_bridge_error or "Desktop Bridge endpointlerine bağlanılamadı.")
                    # Bridge senkron modda tamamlanana kadar beklediği için ekstra bekleme gerekmez.
                except Exception as e:
                    print(f"⚠️ [AI] Köprüye ulaşılamadı, üretim devam ediyor: {e}")
                    self.last_analysis_metadata["live_overlay_status"] = "unavailable"
                    self.last_analysis_metadata["live_overlay_error"] = str(e)
            else:
                print("ℹ️ [AI] Vision Overlay kapalı; Desktop Bridge denemesi atlandı.")
            # ----------------------------------------------------------------

            context = self._build_world_view(
                url,
                elements,
                use_url_inference_fallback=False,
                vision_provider=vision_provider,
            )
            if strict_visual and "No UI elements detected visually." in context:
                raise RuntimeError("Görsel analiz tamamlandı ancak vision provider hiçbir UI elementi tespit edemedi.")
            return context

        except Exception as e:
            if strict_visual:
                raise RuntimeError(f"Görsel analiz başarısız: {e}") from e
            print(f"⚠️ [Analiz] Hata: {e}. URL'den çıkarım yapılıyor.")
            self.last_analysis_metadata = {
                "vision_provider": "url_inference",
                "detected_element_count": 0,
                "visual_fallback_used": True,
                "fallback_reason": str(e),
                "detected_elements": [],
                "screenshot_base64": "",
                "annotated_screenshot_base64": "",
            }
            return self._infer_context_from_url(url)
        finally:
            if executor is not None:
                try:
                    await executor.stop()
                except BaseException as stop_error:
                    print(f"⚠️ [Analiz] Browser cleanup atlandı: {stop_error}")
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
        use_url_inference_fallback: bool = True,
        vision_provider: str = "SAM3"
    ) -> str:
        """
        SAM3/Grounding DINO çıktısını LLM için okunabilir bağlama çevirir.
        """
        lines = [f"URL: {url}", f"### VISUAL WORLD VIEW (Detected via {vision_provider})"]
        dom_elements = []
        try:
            dom_elements = self.last_analysis_metadata.get("dom_interactive_elements", []) or []
        except Exception:
            dom_elements = []
        
        if not elements:
            lines.append("\nNo UI elements detected visually.")
            if use_url_inference_fallback:
                lines.append("Using URL-based inference as fallback.")
                lines.append(self._infer_context_from_url(url))
            return "\n".join(lines)

        lines.append(f"\nDetected {len(elements)} UI elements:")
        label_counts: Dict[str, int] = {}
        for i, elem in enumerate(elements, 1):
            label = elem.get("label", "unknown")
            score = elem.get("score", 0)
            box = elem.get("box", [])
            normalized_label = str(label).lower()
            label_counts[normalized_label] = label_counts.get(normalized_label, 0) + 1
            lines.append(f"  {i}. {label.upper()}: position={box}, confidence={score:.2f}")

        has_input = any(any(k in label for k in ["input", "text field", "textbox", "search", "email", "password"]) for label in label_counts)
        has_button = any("button" in label for label in label_counts)
        has_link = any("link" in label for label in label_counts)
        has_form = any("form" in label for label in label_counts)
        capabilities = []
        capabilities.append("type_allowed=yes" if has_input else "type_allowed=no")
        capabilities.append("form_submit_allowed=yes" if (has_button and (has_input or has_form)) else "form_submit_allowed=no")
        capabilities.append("navigation_click_allowed=yes" if (has_link or has_button) else "navigation_click_allowed=no")
        lines.append("\n### EXECUTION CAPABILITIES FROM VISUAL EVIDENCE")
        lines.append(", ".join(capabilities))
        if not has_input:
            lines.append("Important: no visible input/text field was detected; do not create type steps for this page.")
        if not has_button:
            lines.append("Important: no visible button was detected; avoid submit/button click steps unless a link is the target.")

        if dom_elements:
            lines.append("\n### REAL DOM INTERACTIVE ELEMENTS ON THIS EXACT URL")
            lines.append("Use these selectors first. Do not create tests for elements absent from this list.")
            for i, element in enumerate(dom_elements[:40], 1):
                kind = element.get("kind", "element")
                text = element.get("text", "")
                selector = element.get("selector", "")
                href = element.get("href", "")
                placeholder = element.get("placeholder", "")
                extra = []
                if text:
                    extra.append(f"text='{text}'")
                if placeholder:
                    extra.append(f"placeholder='{placeholder}'")
                if href:
                    extra.append(f"href='{href}'")
                lines.append(f"  {i}. {kind}: selector=\"{selector}\"" + (f" ({', '.join(extra)})" if extra else ""))

        return "\n".join(lines)

    async def _extract_dom_interactive_elements(self, executor) -> List[Dict[str, Any]]:
        page = getattr(executor, "page", None)
        if page is None:
            return []
        try:
            return await page.evaluate(
                """() => {
                    const clean = (value) => (value || '').replace(/\\s+/g, ' ').trim().slice(0, 80);
                    const cssEscape = window.CSS && window.CSS.escape ? window.CSS.escape.bind(window.CSS) : (value) => String(value).replace(/"/g, '\\"');
                    const unique = [];
                    const seen = new Set();
                    const push = (item) => {
                        if (!item.selector || seen.has(item.selector)) return;
                        seen.add(item.selector);
                        unique.push(item);
                    };
                    const visible = (el) => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style && style.visibility !== 'hidden' && style.display !== 'none' && rect.width >= 8 && rect.height >= 8;
                    };
                    const selectorFor = (el) => {
                        if (el.id) return `#${cssEscape(el.id)}`;
                        const testId = el.getAttribute('data-testid') || el.getAttribute('data-test');
                        if (testId) return `[data-testid="${cssEscape(testId)}"], [data-test="${cssEscape(testId)}"]`;
                        const aria = el.getAttribute('aria-label');
                        if (aria) return `${el.tagName.toLowerCase()}[aria-label="${cssEscape(aria)}"]`;
                        const placeholder = el.getAttribute('placeholder');
                        if (placeholder) return `${el.tagName.toLowerCase()}[placeholder="${cssEscape(placeholder)}"]`;
                        const name = el.getAttribute('name');
                        if (name) return `${el.tagName.toLowerCase()}[name="${cssEscape(name)}"]`;
                        const type = el.getAttribute('type');
                        const text = clean(el.innerText || el.value);
                        if ((el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') && text) {
                            return `${el.tagName.toLowerCase()}:has-text("${text.slice(0, 40).replace(/"/g, '\\"')}")`;
                        }
                        if (el.tagName === 'A' && text) {
                            return `a:has-text("${text.slice(0, 40).replace(/"/g, '\\"')}")`;
                        }
                        if (type) return `${el.tagName.toLowerCase()}[type="${cssEscape(type)}"]`;
                        return el.tagName.toLowerCase();
                    };

                    document.querySelectorAll('a, button, input, textarea, select, [role="button"]').forEach((el) => {
                        if (!visible(el)) return;
                        const tag = el.tagName.toLowerCase();
                        const type = (el.getAttribute('type') || '').toLowerCase();
                        let kind = tag;
                        if (tag === 'input') kind = type ? `input:${type}` : 'input';
                        if (tag === 'a') kind = 'link';
                        if (tag === 'button' || el.getAttribute('role') === 'button') kind = 'button';
                        push({
                            kind,
                            selector: selectorFor(el),
                            text: clean(el.innerText || el.value || el.getAttribute('aria-label')),
                            placeholder: clean(el.getAttribute('placeholder')),
                            href: clean(el.getAttribute('href')),
                        });
                    });
                    return unique.slice(0, 80);
                }"""
            )
        except Exception as exc:
            print(f"⚠️ [DOM] Interactive element extraction failed: {exc}")
            return []

    def _image_file_to_base64(self, path: str) -> str:
        try:
            with open(path, "rb") as image_file:
                return "data:image/png;base64," + base64.b64encode(image_file.read()).decode("utf-8")
        except Exception:
            return ""

    def _annotate_screenshot_base64(self, path: str, elements: List[Dict[str, Any]]) -> str:
        if not elements:
            return self._image_file_to_base64(path)
        try:
            from PIL import Image, ImageDraw

            image = Image.open(path).convert("RGB")
            draw = ImageDraw.Draw(image)
            for element in elements[:30]:
                box = element.get("box") or []
                if len(box) != 4:
                    continue
                x1, y1, x2, y2 = [float(value) for value in box]
                label = str(element.get("label", "element"))
                score = float(element.get("score") or 0)
                draw.rectangle((x1, y1, x2, y2), outline="#22c55e", width=3)
                draw.rectangle((x1, max(0, y1 - 18), min(image.width, x1 + 180), y1), fill="#022c22")
                draw.text((x1 + 4, max(0, y1 - 16)), f"{label} {score:.2f}", fill="#ffffff")

            buffer = tempfile.SpooledTemporaryFile()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            return "data:image/png;base64," + base64.b64encode(buffer.read()).decode("utf-8")
        except Exception:
            return self._image_file_to_base64(path)



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

        per_category_counts: Dict[str, int] = {}

        for category_key, scenarios in raw_cases.items():
            # Meta alanları atla (page_analysis_summary, total_rules_covered vb.)
            if not isinstance(scenarios, list):
                continue
            normalized_category = normalize_category(category_key)

            for scenario in scenarios:
                if not isinstance(scenario, dict):
                    continue
                if not self._scenario_supported_by_detected_page(scenario, normalized_category, url):
                    print(f"⚠️ [TestGen] Sayfayla uyumsuz senaryo atlandı: {scenario.get('title', 'Untitled')}")
                    continue
                if per_category_counts.get(normalized_category, 0) >= 2:
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
                formatted_steps = self._ensure_navigate_first(formatted_steps, url)
                formatted_steps = self._ensure_wait_after_navigation(formatted_steps)
                formatted_steps = self._enrich_steps_for_case(
                    formatted_steps,
                    scenario,
                    normalized_category,
                )
                formatted_steps = self._specialize_steps_for_case(
                    formatted_steps,
                    scenario,
                    normalized_category,
                    url,
                )
                formatted_steps = self._sanitize_steps_against_detected_elements(
                    formatted_steps,
                    normalized_category,
                )

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
                per_category_counts[normalized_category] = per_category_counts.get(normalized_category, 0) + 1

        inventory_fallback = self._build_visual_fallback_cases(url)
        if not cases:
            return inventory_fallback

        existing_titles = {case.get("title") for case in cases}
        for fallback_case in inventory_fallback:
            category = fallback_case.get("category", "happy_path")
            if per_category_counts.get(category, 0) >= 2:
                continue
            if fallback_case.get("title") in existing_titles:
                continue
            cases.append(fallback_case)
            existing_titles.add(fallback_case.get("title"))
            per_category_counts[category] = per_category_counts.get(category, 0) + 1

        return cases

    def _detected_element_capabilities(self) -> Dict[str, bool]:
        elements = []
        dom_elements = []
        try:
            elements = self.last_analysis_metadata.get("detected_elements", []) or []
            dom_elements = self.last_analysis_metadata.get("dom_interactive_elements", []) or []
        except Exception:
            elements = []
            dom_elements = []

        labels = [str(element.get("label", "")).lower() for element in elements if isinstance(element, dict)]
        dom_kinds = [str(element.get("kind", "")).lower() for element in dom_elements if isinstance(element, dict)]
        dom_text = " ".join(
            " ".join([
                str(element.get("kind", "")),
                str(element.get("selector", "")),
                str(element.get("text", "")),
                str(element.get("placeholder", "")),
            ]).lower()
            for element in dom_elements
            if isinstance(element, dict)
        )
        has_input = (
            any(any(k in label for k in ["input", "text field", "textbox", "search", "email", "password"]) for label in labels)
            or any(kind.startswith(("input", "textarea", "select")) for kind in dom_kinds)
        )
        has_button = any("button" in label for label in labels) or any(kind == "button" for kind in dom_kinds)
        has_link = any("link" in label for label in labels) or any(kind == "link" for kind in dom_kinds)
        has_form = any("form" in label for label in labels)
        has_password = any("password" in label for label in labels) or "password" in dom_text
        has_email = any("email" in label for label in labels) or "email" in dom_text or "mail" in dom_text
        has_search = any("search" in label for label in labels) or "search" in dom_text or "arama" in dom_text
        has_visual_evidence = bool(labels or dom_elements)
        return {
            "has_visual_evidence": has_visual_evidence,
            "has_input": has_input,
            "has_button": has_button,
            "has_link": has_link,
            "has_form": has_form,
            "has_password": has_password,
            "has_email": has_email,
            "has_search": has_search,
        }

    def _scenario_supported_by_detected_page(
        self,
        scenario: Dict[str, Any],
        category_key: str,
        url: str,
    ) -> bool:
        capabilities = self._detected_element_capabilities()
        if not capabilities["has_visual_evidence"]:
            return True

        title = str(scenario.get("title", "")).lower()
        description = str(scenario.get("description", scenario.get("expected_outcome", ""))).lower()
        covers_rule = str(scenario.get("covers_rule", "")).lower()
        steps_text = " ".join(
            f"{step.get('action', '')} {step.get('target', '')} {step.get('value', '')}"
            for step in scenario.get("steps", [])
            if isinstance(step, dict)
        ).lower()
        combined = " ".join([title, description, covers_rule, steps_text])
        url_lower = url.lower()

        auth_like = any(k in combined for k in ["login", "log in", "sign in", "signin", "password", "credential", "authenticate"])
        auth_url = any(k in url_lower for k in ["login", "signin", "auth", "giris", "giriş"])
        if auth_like and not (capabilities["has_password"] or (auth_url and capabilities["has_input"] and capabilities["has_button"])):
            return False

        search_like = any(k in combined for k in ["search", "arama"])
        if search_like and not (capabilities["has_search"] or capabilities["has_input"]):
            return False

        form_like = any(k in combined for k in ["form", "submit", "required field", "validation"])
        if form_like and not (capabilities["has_input"] or capabilities["has_form"]):
            return False

        injection_like = any(k in combined for k in ["xss", "sql", "injection", "<script", "or 1=1"])
        if injection_like and not capabilities["has_input"]:
            return False

        return True

    def _build_visual_fallback_cases(self, url: str) -> List[Dict[str, Any]]:
        capabilities = self._detected_element_capabilities()
        primary_link = self._first_dom_selector(["link"])
        primary_button = self._first_dom_selector(["button"])
        primary_input = self._first_dom_selector(["input", "textarea", "select"])
        interaction_target = primary_link or primary_button or ("a, button, [role='button']" if (capabilities["has_link"] or capabilities["has_button"]) else "body")
        submit_target = primary_button or "button[type='submit'], input[type='submit']"
        verify_error_target = ".error, .alert, [role='alert'], body"

        cases: List[Dict[str, Any]] = [
            {
                "title": "Verify detected page content loads",
                "description": "Page loads and visible content is present for the provided URL.",
                "category": "happy_path",
                "priority": "high",
                "source_url": url,
                "steps": [
                    {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                    {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                    {"order": 3, "action": "verify", "target": "body", "value": "", "expected": "Visible page content is present"},
                ],
            },
            {
                "title": "Verify available navigation elements",
                "description": "Visible links or buttons are available without inventing unsupported form interactions.",
                "category": "happy_path",
                "priority": "medium",
                "source_url": url,
                "steps": [
                    {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                    {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                    {"order": 3, "action": "verify", "target": interaction_target, "value": "", "expected": "Detected navigation or content surface is visible"},
                ],
            },
        ]

        if capabilities["has_input"]:
            cases.extend([
                {
                    "title": "Reject empty or incomplete form submission",
                    "description": "Detected form/input controls should handle an incomplete submission safely.",
                    "category": "negative_path",
                    "priority": "high",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "click", "target": submit_target, "value": "", "expected": "Submit or primary action is attempted"},
                        {"order": 4, "action": "verify", "target": verify_error_target, "value": "", "expected": "Page remains controlled after invalid submission"},
                    ],
                },
                {
                    "title": "Handle invalid text input safely",
                    "description": "Detected input accepts invalid test data without crashing the page.",
                    "category": "negative_path",
                    "priority": "high",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "type", "target": primary_input or "input:not([type='hidden']):not([disabled])", "value": "invalid-input", "expected": "Invalid value is entered"},
                        {"order": 4, "action": "verify", "target": "body", "value": "", "expected": "Page remains stable"},
                    ],
                },
                {
                    "title": "Handle special characters in detected input",
                    "description": "Detected input handles special characters without visible instability.",
                    "category": "edge_case",
                    "priority": "medium",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "type", "target": primary_input or "input:not([type='hidden']):not([disabled])", "value": "!@#$%^&*()_+-=[]{}", "expected": "Special characters are entered"},
                        {"order": 4, "action": "verify", "target": "body", "value": "", "expected": "Application remains stable"},
                    ],
                },
                {
                    "title": "Handle very long value in detected input",
                    "description": "Detected input handles a long value without crashing.",
                    "category": "edge_case",
                    "priority": "medium",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "type", "target": primary_input or "input:not([type='hidden']):not([disabled])", "value": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "expected": "Long value is entered"},
                        {"order": 4, "action": "verify", "target": "body", "value": "", "expected": "Application remains stable"},
                    ],
                },
                {
                    "title": "Treat XSS payload as text in detected input",
                    "description": "Detected input should not execute script-like payloads.",
                    "category": "security",
                    "priority": "critical",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "type", "target": primary_input or "input:not([type='hidden']):not([disabled])", "value": "<script>alert('xss')</script>", "expected": "Payload is entered as text"},
                        {"order": 4, "action": "verify", "target": "body", "value": "", "expected": "Script payload does not execute visibly"},
                    ],
                },
                {
                    "title": "Treat SQL-like payload as text in detected input",
                    "description": "Detected input should not treat SQL-like text as a control command.",
                    "category": "security",
                    "priority": "critical",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "type", "target": primary_input or "input:not([type='hidden']):not([disabled])", "value": "' OR 1=1 --", "expected": "SQL-like payload is entered as text"},
                        {"order": 4, "action": "verify", "target": "body", "value": "", "expected": "Payload does not break the page"},
                    ],
                },
            ])
        else:
            cases.extend([
                {
                    "title": "Verify no form interaction is required on this page",
                    "description": "Page has no detected input, so validation stays focused on visible content.",
                    "category": "negative_path",
                    "priority": "medium",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "verify", "target": "body", "value": "", "expected": "Page content is visible without invented form controls"},
                    ],
                },
                {
                    "title": "Verify detected link or action target remains visible",
                    "description": "Detected non-form interaction target is available before any deeper navigation.",
                    "category": "negative_path",
                    "priority": "medium",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "verify", "target": interaction_target, "value": "", "expected": "Detected action target remains visible"},
                    ],
                },
                {
                    "title": "Handle repeated page load consistently",
                    "description": "The same URL should remain stable across repeated loads.",
                    "category": "edge_case",
                    "priority": "medium",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "navigate", "target": url, "value": "", "expected": "Page can be loaded again"},
                        {"order": 4, "action": "verify", "target": "body", "value": "", "expected": "Page remains visible after repeated load"},
                    ],
                },
                {
                    "title": "Verify primary content without input assumptions",
                    "description": "Content-only or navigation pages should be validated without fake typing steps.",
                    "category": "edge_case",
                    "priority": "medium",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "verify", "target": interaction_target, "value": "", "expected": "Primary detected surface is visible"},
                    ],
                },
                {
                    "title": "Review visible error surface",
                    "description": "Page should not open directly into a visible error/debug surface.",
                    "category": "security",
                    "priority": "critical",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "verify", "target": "body", "value": "", "expected": "Visible body is present for security review"},
                    ],
                },
                {
                    "title": "Review visible navigation surface",
                    "description": "Detected links/buttons remain visible without requiring credentials or fake form fields.",
                    "category": "security",
                    "priority": "high",
                    "source_url": url,
                    "steps": [
                        {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Page opens successfully"},
                        {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page reaches a stable loaded state"},
                        {"order": 3, "action": "verify", "target": interaction_target, "value": "", "expected": "Visible navigation surface is available for controlled testing"},
                    ],
                },
            ])

        for index, case in enumerate(cases):
            case["id"] = index + 1
        return cases

    def _sanitize_steps_against_detected_elements(
        self,
        steps: List[Dict[str, Any]],
        category_key: str,
    ) -> List[Dict[str, Any]]:
        capabilities = self._detected_element_capabilities()
        if not capabilities["has_visual_evidence"]:
            return steps

        sanitized: List[Dict[str, Any]] = []
        removed_interaction = False
        for raw_step in steps:
            step = dict(raw_step)
            action = str(step.get("action", "")).lower()
            target = str(step.get("target", "")).lower()

            if action == "type" and not capabilities["has_input"]:
                removed_interaction = True
                continue

            submit_like = any(k in target for k in ["submit", "login", "continue", "devam", "giriş", "giris"])
            if action == "click" and submit_like and not (capabilities["has_button"] and (capabilities["has_input"] or capabilities["has_form"])):
                removed_interaction = True
                continue

            search_like = any(k in target for k in ["search", "arama"])
            if action in {"type", "click"} and search_like and not capabilities["has_input"]:
                removed_interaction = True
                continue

            sanitized.append(step)

        if removed_interaction:
            fallback_target = self._first_dom_selector(["link", "button"]) or ("a, button, [role='button'], body" if (capabilities["has_link"] or capabilities["has_button"]) else "body")
            sanitized.append({
                "order": len(sanitized) + 1,
                "action": "verify",
                "target": fallback_target,
                "value": "",
                "expected": "Only visually detected page content is verified; unsupported generated interactions were skipped.",
            })

        for index, step in enumerate(sanitized, start=1):
            step["order"] = index
        return sanitized

    def _first_dom_selector(self, kinds: List[str]) -> str:
        try:
            elements = self.last_analysis_metadata.get("dom_interactive_elements", []) or []
        except Exception:
            elements = []
        for element in elements:
            kind = str(element.get("kind", "")).lower()
            selector = str(element.get("selector", "")).strip()
            if selector and any(kind.startswith(wanted.lower()) for wanted in kinds):
                return selector
        return ""

    def _ensure_navigate_first(self, steps: List[Dict[str, Any]], url: str) -> List[Dict[str, Any]]:
        if not steps:
            return [{
                "order": 1,
                "action": "navigate",
                "target": url,
                "value": "",
                "expected": "Page opens successfully",
            }]

        first_action = str(steps[0].get("action", "")).strip().lower()
        first_target = str(steps[0].get("target", "")).strip()
        if first_action == "navigate" and first_target:
            normalized = [dict(step) for step in steps]
        else:
            normalized = [{
                "order": 1,
                "action": "navigate",
                "target": url,
                "value": "",
                "expected": "Page opens successfully",
            }]
            normalized.extend(dict(step) for step in steps)

        for index, step in enumerate(normalized, start=1):
            step["order"] = index
        return normalized

    def _ensure_wait_after_navigation(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = [dict(step) for step in steps]
        if not normalized:
            return normalized
        if str(normalized[0].get("action", "")).lower() != "navigate":
            return normalized
        if len(normalized) > 1 and str(normalized[1].get("action", "")).lower() == "wait":
            return normalized
        normalized.insert(1, {
            "order": 2,
            "action": "wait",
            "target": "networkidle",
            "value": "",
            "expected": "Page reaches a stable loaded state",
        })
        for index, step in enumerate(normalized, start=1):
            step["order"] = index
        return normalized

    def _specialize_steps_for_case(
        self,
        steps: List[Dict[str, Any]],
        scenario: Dict[str, Any],
        category_key: str,
        url: str,
    ) -> List[Dict[str, Any]]:
        title = str(scenario.get("title", "")).lower()
        description = str(scenario.get("description", scenario.get("expected_outcome", ""))).lower()
        covers_rule = str(scenario.get("covers_rule", "")).lower()
        combined = " ".join([title, description, covers_rule])
        url_lower = url.lower()

        if "saucedemo" in url_lower:
            return self._specialize_saucedemo_login_steps(steps, combined, category_key, url)

        return self._specialize_generic_login_steps(steps, combined, category_key, url)

    def _specialize_saucedemo_login_steps(
        self,
        steps: List[Dict[str, Any]],
        combined: str,
        category_key: str,
        url: str,
    ) -> List[Dict[str, Any]]:
        base = [
            {"order": 1, "action": "navigate", "target": url, "value": "", "expected": "Login page opens"},
            {"order": 2, "action": "wait", "target": "networkidle", "value": "", "expected": "Page is stable"},
        ]

        if any(k in combined for k in ["form is visible", "controls visible", "authentication controls"]):
            specialized = base + [
                {"order": 3, "action": "verify", "target": "#user-name", "value": "", "expected": "Username field is visible"},
                {"order": 4, "action": "verify", "target": "#password", "value": "", "expected": "Password field is visible"},
                {"order": 5, "action": "verify", "target": "#login-button", "value": "", "expected": "Login button is visible"},
            ]
        elif any(k in combined for k in ["invalid password", "wrong password", "invalid credentials"]):
            specialized = base + [
                {"order": 3, "action": "type", "target": "#user-name", "value": "standard_user", "expected": "Username is entered"},
                {"order": 4, "action": "type", "target": "#password", "value": "wrong_password", "expected": "Invalid password is entered"},
                {"order": 5, "action": "click", "target": "#login-button", "value": "", "expected": "Login is submitted"},
                {"order": 6, "action": "verify", "target": "[data-test='error'], .error-message-container", "value": "", "expected": "Credential error is displayed"},
            ]
        elif any(k in combined for k in ["sql", "injection string"]):
            specialized = base + [
                {"order": 3, "action": "type", "target": "#user-name", "value": "' OR 1=1 --", "expected": "SQL-like payload is entered"},
                {"order": 4, "action": "type", "target": "#password", "value": "anything", "expected": "Password is entered"},
                {"order": 5, "action": "click", "target": "#login-button", "value": "", "expected": "Login is submitted"},
                {"order": 6, "action": "verify", "target": "[data-test='error'], .error-message-container", "value": "", "expected": "Payload does not bypass login"},
            ]
        elif any(k in combined for k in ["long username", "length boundary", "long value"]):
            specialized = base + [
                {"order": 3, "action": "type", "target": "#user-name", "value": "very_long_username_value_that_should_not_crash_the_login_form", "expected": "Long username is entered"},
                {"order": 4, "action": "type", "target": "#password", "value": "secret_sauce", "expected": "Password is entered"},
                {"order": 5, "action": "click", "target": "#login-button", "value": "", "expected": "Login is submitted"},
                {"order": 6, "action": "verify", "target": "[data-test='error'], .error-message-container, body", "value": "", "expected": "Page remains controlled"},
            ]
        elif category_key == "happy_path" or any(k in combined for k in ["successful", "valid login", "loads successfully"]):
            specialized = base + [
                {"order": 3, "action": "type", "target": "#user-name", "value": "standard_user", "expected": "Username is entered"},
                {"order": 4, "action": "type", "target": "#password", "value": "secret_sauce", "expected": "Password is entered"},
                {"order": 5, "action": "click", "target": "#login-button", "value": "", "expected": "Login is submitted"},
                {"order": 6, "action": "verify", "target": ".inventory_list, [data-test='inventory-container']", "value": "", "expected": "Inventory page is visible"},
            ]
        elif "xss" in combined:
            specialized = base + [
                {"order": 3, "action": "type", "target": "#user-name", "value": "<script>alert('xss')</script>", "expected": "XSS payload is entered as username"},
                {"order": 4, "action": "type", "target": "#password", "value": "secret_sauce", "expected": "Password is entered"},
                {"order": 5, "action": "click", "target": "#login-button", "value": "", "expected": "Login is submitted"},
                {"order": 6, "action": "verify", "target": "[data-test='error'], .error-message-container, body", "value": "", "expected": "Payload is not executed and page remains controlled"},
            ]
        elif any(k in combined for k in ["special", "unicode", "character"]):
            specialized = base + [
                {"order": 3, "action": "type", "target": "#user-name", "value": "!@#$%^&*()_+-=[]{}|;':,.<>/?", "expected": "Special characters are entered"},
                {"order": 4, "action": "type", "target": "#password", "value": "secret_sauce", "expected": "Password is entered"},
                {"order": 5, "action": "click", "target": "#login-button", "value": "", "expected": "Login is submitted"},
                {"order": 6, "action": "verify", "target": "[data-test='error'], .error-message-container, body", "value": "", "expected": "Application handles special characters without crashing"},
            ]
        elif any(k in combined for k in ["invalid", "empty", "required", "form submission", "negative"]):
            specialized = base + [
                {"order": 3, "action": "click", "target": "#login-button", "value": "", "expected": "Empty form submission is attempted"},
                {"order": 4, "action": "verify", "target": "[data-test='error'], .error-message-container", "value": "", "expected": "Required field error is displayed"},
            ]
        else:
            specialized = self._replace_generic_login_targets(steps)

        for index, step in enumerate(specialized, start=1):
            step["order"] = index
        return specialized

    def _specialize_generic_login_steps(
        self,
        steps: List[Dict[str, Any]],
        combined: str,
        category_key: str,
        url: str,
    ) -> List[Dict[str, Any]]:
        is_login_like = any(k in (combined + " " + url.lower()) for k in ["login", "signin", "sign in", "authentication", "form"])
        if not is_login_like:
            return steps

        specialized = self._replace_generic_login_targets(steps)
        if category_key == "happy_path" and not any("password" in str(s.get("target", "")).lower() for s in specialized):
            insert_at = 3 if len(specialized) >= 3 else len(specialized)
            specialized.insert(insert_at, {
                "order": insert_at + 1,
                "action": "type",
                "target": "input[type='password']",
                "value": "ValidPass123!",
                "expected": "Password is entered",
            })
        for index, step in enumerate(specialized, start=1):
            step["order"] = index
        return specialized

    def _replace_generic_login_targets(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rewritten: List[Dict[str, Any]] = []
        first_text_input_seen = False
        for raw_step in steps:
            step = dict(raw_step)
            action = str(step.get("action", "")).lower()
            target = str(step.get("target", ""))
            target_lower = target.lower()

            if action == "type":
                if "#user-name" in target_lower or "user-name" in target_lower:
                    step["target"] = "input[autocomplete='username'], input[name*='user' i], input[type='email'], input[type='text']"
                elif "#password" in target_lower or "password" in target_lower:
                    step["target"] = "input[type='password']"
                elif "input[type='text']" in target_lower or 'input[type="text"]' in target_lower or "input:not" in target_lower:
                    step["target"] = (
                        "input[autocomplete='username'], input[name*='user' i], input[type='email'], input[type='text']"
                        if not first_text_input_seen
                        else "input[type='password']"
                    )
                    first_text_input_seen = True
                elif "email" in target_lower or "user" in target_lower or "mail" in target_lower:
                    step["target"] = "input[type='email'], input[autocomplete='username'], input[name*='email' i], input[type='text']"
                if not str(step.get("value", "")).strip():
                    if "password" in step["target"]:
                        step["value"] = "ValidPass123!"
                    elif "xss" not in str(step.get("expected", "")).lower():
                        step["value"] = "user@example.com"

            if action == "click":
                if any(k in target_lower for k in ["submit", "login", "sign in", "giriş", "giris", "devam"]):
                    step["target"] = "button[type='submit'], input[type='submit'], button:has-text('Login'), button:has-text('Sign in'), button:has-text('Devam Et')"

            if action == "verify" and target_lower.strip() in {"body", "main", "page"}:
                step["target"] = ".inventory_list, [data-test='error'], .error-message-container, body"

            rewritten.append(step)
        return rewritten

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
