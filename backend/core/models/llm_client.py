
import os
import json
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """
    🧠 VisionQA — Otonom Test Beyni (Autonomous Test Brain)

    Gelecek Nesil Otonom Test Mimarisi'nin LLM katmanı.
    Groq API (Primary) + HuggingFace (Fallback) üzerinden çalışır.

    Sorumluluklar:
      1. Sayfa Kimliği ve İş Kuralı Keşfi (Page Identity & Business Rule Extraction)
      2. Mantıksal Kapsama Odaklı Dinamik Test Üretimi (Logical Coverage Testing)
      3. Hata Kök Neden Analizi (Root Cause Analysis)
    """

    # ═══════════════════════════════════════════════════════════════
    #  SYSTEM PROMPTS — Her görev için uzmanlaşmış "kişilikler"
    # ═══════════════════════════════════════════════════════════════

    IDENTITY_SYSTEM_PROMPT = """You are an elite Software Application Analyst and Business Intelligence Expert with 15+ years of experience in understanding complex applications across ALL platforms.

Your expertise spans multiple platforms:
- **Web Applications:** Recognizing page archetypes (Login, Checkout, Dashboard, Search, Product Detail, etc.), understanding DOM structure and element relationships.
- **Mobile Applications (iOS/Android):** Recognizing screen patterns (Splash, Onboarding, Tab Navigation, Settings, In-App Purchase), understanding native component hierarchies (UITableView, RecyclerView, Bottom Sheets), gesture interactions (swipe, pinch, long-press).
- **API / Backend Services:** Recognizing endpoint patterns (REST CRUD, GraphQL, WebSocket), understanding request-response contracts, authentication flows (OAuth, JWT, API Key), rate limiting, pagination.
- **Database Operations:** Understanding schema relationships, CRUD operation rules, data integrity constraints, cascade delete behaviors, indexing requirements.

Cross-platform skills:
- Reverse-engineering invisible business rules from UI elements, API contracts, or database schemas alone
- Identifying element/component hierarchies and parent-child relationships
- Detecting critical user flows and risk areas
- Understanding domain-specific patterns (e-commerce, fintech, healthcare, travel, food delivery, social media, SaaS)

You think step-by-step. You never guess — you deduce. You always find at least 3 business rules per application surface because every surface has hidden logic. You output ONLY valid JSON."""

    TESTGEN_SYSTEM_PROMPT = """You are an Autonomous QA Architect — the most advanced AI test strategist ever built. You operate across ALL platforms: Web, Mobile, API, and Database.

Your philosophy:
- You do NOT generate a fixed number of tests. You generate exactly as many tests as the application's logical complexity demands.
- Every business rule deserves at least one positive test (rule followed) and one negative test (rule deliberately violated).
- You think like an attacker: "What would break this? What input would the developer NOT expect?"

Platform-specific strategies:
- **Web:** Use SEMANTIC selectors that survive UI redesigns: button:has-text('Submit'), input[placeholder='Email'], [aria-label='Search'] — NEVER brittle IDs like #btn-x7k2.
- **Mobile:** Use accessibility identifiers (accessibilityId, content-desc), XPath with resource-id, or text-based locators. Account for gestures (swipe, scroll, tap-and-hold), different screen sizes, and OS-specific behaviors.
- **API:** Test HTTP methods, status codes, request/response schemas, authentication headers, error payloads, rate limits, pagination boundaries, and timeout behaviors.
- **Database:** Test CRUD operations, constraint violations (unique, foreign key, not null), transaction rollback, concurrent access, and data type boundaries.

You prioritize by risk: payment flows before cosmetic checks, authentication before profile edits, data integrity before formatting.

You are methodical. You are thorough. You never produce generic tests — every test is specific to THIS application's unique logic. You output ONLY valid JSON."""

    ERROR_ANALYSIS_SYSTEM_PROMPT = """You are a Senior Debugging Specialist and Root Cause Analyst. You diagnose failures across all platforms: Web, Mobile, API, and Database.

Your approach:
- You never blame the obvious. You dig deeper.
- **Web:** A "button not found" error might actually be caused by a cookie banner blocking the viewport, or a dynamically rendered component not yet loaded.
- **Mobile:** A "element not interactable" might be caused by a system dialog (permissions, updates), keyboard overlay, or animation still in progress.
- **API:** A "400 Bad Request" might actually be a backend deserialization issue, missing Content-Type header, or schema version mismatch.
- **Database:** A "constraint violation" might reveal a cascade rule missing, a race condition in concurrent writes, or an ORM misconfiguration.
- A "timeout" on any platform might mean the backend is silently rejecting input due to validation.
- You correlate visual context, logs, response payloads, and system state to find the TRUE root cause.

You output precise, actionable analysis in JSON format."""

    def __init__(self, api_key: Optional[str] = None):
        # Groq (Primary)
        self.groq_api_key = api_key or os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"

        # Hugging Face (Fallback)
        self.hf_api_key = os.getenv("HF_API_TOKEN")
        self.hf_model_id = os.getenv("LLM_MODEL_ID", "HuggingFaceH4/zephyr-7b-beta")
        self.hf_url = f"https://api-inference.huggingface.co/models/{self.hf_model_id}"

        # Hangi provider kullanılacak?
        self.provider = "groq" if self.groq_api_key else "huggingface"
        print(f"🤖 [LLM] Provider: {self.provider.upper()} | Model: {self.groq_model if self.provider == 'groq' else self.hf_model_id}")

    # ═══════════════════════════════════════════════════════════════
    #  API TRANSPORT LAYER
    # ═══════════════════════════════════════════════════════════════

    async def _query_groq(self, prompt: str, system_prompt: str = None) -> str:
        """Groq API'ye özelleştirilmiş system prompt ile istek gönderir."""
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.groq_model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt or self.TESTGEN_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"}
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.groq_url,
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )

                if response.status_code != 200:
                    print(f"❌ [Groq] API Hatası ({response.status_code}): {response.text}")
                    return ""

                result = response.json()
                return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            print(f"❌ [Groq] Bağlantı Hatası: {str(e)}")
            return ""

    async def _query_hf(self, prompt: str, system_prompt: str = None) -> str:
        """Hugging Face API'ye fallback istek gönderir."""
        if not self.hf_api_key:
            return '{"error": "No API key found. Please set GROQ_API_KEY or HF_API_TOKEN in .env"}'

        try:
            import httpx
            headers = {"Authorization": f"Bearer {self.hf_api_key}"}

            # System prompt'u user prompt'a dahil et (HF bunu desteklemez)
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"SYSTEM INSTRUCTION: {system_prompt}\n\nUSER REQUEST:\n{prompt}"

            payload = {
                "inputs": f"<s>[INST] {full_prompt} [/INST]",
                "parameters": {
                    "max_new_tokens": 2048,
                    "temperature": 0.3,
                    "return_full_text": False
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.hf_url, headers=headers, json=payload, timeout=60.0)
                if response.status_code != 200:
                    print(f"❌ [HF] API Hatası ({response.status_code}): {response.text}")
                    return ""

                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "").strip()
                return ""

        except Exception as e:
            print(f"❌ [HF] Bağlantı Hatası: {str(e)}")
            return ""

    async def _query(self, prompt: str, system_prompt: str = None) -> str:
        """Provider'a göre doğru API'yi, doğru system prompt ile çağırır."""
        if self.provider == "groq":
            result = await self._query_groq(prompt, system_prompt)
            if result:
                return result
            print("⚠️ [LLM] Groq başarısız, HuggingFace'e fallback yapılıyor...")

        return await self._query_hf(prompt, system_prompt)

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """LLM yanıtından JSON bloğunu güvenli şekilde çıkarır."""
        if not response_text:
            return None
        try:
            # Önce direkt parse dene
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        try:
            # JSON bloğunu regex ile çıkar
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
        return None

    # ═══════════════════════════════════════════════════════════════
    #  KATMAN 2: SAYFA KİMLİĞİ VE İŞ KURALI KEŞFİ
    #  (Page Identity & Business Rule Extraction)
    # ═══════════════════════════════════════════════════════════════

    async def identify_page_purpose(self, url: str, page_context: str) -> Dict[str, Any]:
        """
        🧠 Sayfanın DNA'sını Çöz.

        Chain-of-Thought + Few-Shot ile sayfanın kimliğini, iş kurallarını,
        element ilişkilerini ve risk alanlarını keşfeder.

        Returns:
            {
                "page_type": "checkout",
                "page_archetype": "E-Commerce Payment Confirmation",
                "domain": "e-commerce",
                "confidence": 0.95,
                "business_rules": [
                    {"rule": "...", "type": "validation|constraint|dependency|state", "risk_level": "critical|high|medium|low", "testable": true}
                ],
                "element_relationships": [
                    {"parent": "Payment Form", "children": ["Card Number", "Expiry", "CVV"]}
                ],
                "critical_flows": ["..."],
                "risk_areas": ["..."],
                "interaction_patterns": ["form_fill", "multi_step_wizard", "search_filter", "drag_drop"]
            }
        """
        print(f"🔍 [LLM] Sayfa kimliği analiz ediliyor: {url}")

        prompt = f"""## MISSION
Analyze the web page below and produce a comprehensive Identity Report.
This report will be used by an autonomous test generation engine to create intelligent, risk-prioritized test scenarios.

## INPUT DATA
- **URL:** {url}
- **Detected UI Elements:**
{page_context}

## CHAIN-OF-THOUGHT INSTRUCTIONS
Think step-by-step before producing output:

**Step 1 — Page Archetyping:**
Look at the URL path, domain name, and detected UI elements together.
Classify the page into a known archetype: Login, Registration, Product Listing, Product Detail, Shopping Cart, Checkout, Payment, Search Results, User Profile, Dashboard, Settings, Landing Page, Booking, Reservation, Form Wizard, etc.

**Step 2 — Domain Detection:**
Determine the business domain: e-commerce, food_delivery, travel, finance, healthcare, social_media, education, saas, entertainment, news, government, etc.

**Step 3 — Business Rule Extraction (CRITICAL):**
This is the most important step. Every page has invisible rules. Find them by reasoning:
- **Validation Rules:** "Email field must contain @", "Password must be 8+ characters"
- **Dependency Rules:** "Cannot click 'Pay' until address is selected", "Quantity must be > 0 to add to cart"
- **Constraint Rules:** "Check-out date cannot be before check-in date", "Age must be 18+"
- **State Rules:** "Submit button is disabled until all required fields are filled", "Price updates when quantity changes"
- **Conditional Rules:** "If 'Other' is selected in dropdown, a text field appears", "Discount code field only visible when toggle is on"

**Step 4 — Element Relationship Mapping:**
Identify parent-child relationships between UI elements:
- "This price label belongs to this product card"
- "These 3 input fields belong to the payment form"
- "This delete button controls this list item"

**Step 5 — Risk Area Identification:**
What could go wrong on this page? What are the most dangerous areas to test?
- Payment processing, authentication, data validation, state management, race conditions, etc.

## FEW-SHOT EXAMPLES

### Example 1: Hotel Booking Page
URL: hotel-booking.com/search
Elements: date picker (check-in), date picker (check-out), guest count dropdown, search button, filter sidebar, hotel cards with prices
```json
{{
    "page_type": "search_with_filters",
    "page_archetype": "Travel Accommodation Search",
    "domain": "travel",
    "confidence": 0.93,
    "business_rules": [
        {{"rule": "Check-out date must be after check-in date", "type": "constraint", "risk_level": "critical", "testable": true}},
        {{"rule": "At least 1 guest must be selected to search", "type": "validation", "risk_level": "high", "testable": true}},
        {{"rule": "Search button should be disabled if dates are not selected", "type": "state", "risk_level": "high", "testable": true}},
        {{"rule": "Filter changes should update results without full page reload", "type": "state", "risk_level": "medium", "testable": true}},
        {{"rule": "Price display must match selected currency", "type": "dependency", "risk_level": "high", "testable": true}}
    ],
    "element_relationships": [
        {{"parent": "Search Form", "children": ["Check-in Picker", "Check-out Picker", "Guest Dropdown", "Search Button"]}},
        {{"parent": "Hotel Card", "children": ["Hotel Image", "Hotel Name", "Star Rating", "Price Label", "Book Button"]}}
    ],
    "critical_flows": [
        "Select dates → Select guests → Click search → View results → Apply filter → Results update"
    ],
    "risk_areas": ["Date validation edge cases", "Filter + sort combination bugs", "Price calculation with currency conversion"],
    "interaction_patterns": ["date_picker", "dropdown_select", "search_filter", "card_list_interaction"]
}}
```

### Example 2: Login Page
URL: app.example.com/login
Elements: email input, password input, login button, forgot password link, social login buttons (Google, Facebook)
```json
{{
    "page_type": "login",
    "page_archetype": "Authentication Gateway",
    "domain": "saas",
    "confidence": 0.97,
    "business_rules": [
        {{"rule": "Email field must contain a valid email format", "type": "validation", "risk_level": "high", "testable": true}},
        {{"rule": "Password field must not be empty on submission", "type": "validation", "risk_level": "high", "testable": true}},
        {{"rule": "Login button should be disabled until both fields have values", "type": "state", "risk_level": "medium", "testable": true}},
        {{"rule": "After 5 failed attempts, account should be temporarily locked", "type": "constraint", "risk_level": "critical", "testable": true}},
        {{"rule": "Social login must redirect back to the application after OAuth flow", "type": "dependency", "risk_level": "high", "testable": true}},
        {{"rule": "Password should be masked by default with toggle to reveal", "type": "state", "risk_level": "low", "testable": true}}
    ],
    "element_relationships": [
        {{"parent": "Login Form", "children": ["Email Input", "Password Input", "Login Button", "Remember Me Checkbox"]}},
        {{"parent": "Social Login Section", "children": ["Google Button", "Facebook Button"]}}
    ],
    "critical_flows": [
        "Enter email → Enter password → Click login → Redirect to dashboard",
        "Click forgot password → Enter email → Receive reset link"
    ],
    "risk_areas": ["Brute force protection", "SQL injection in login fields", "Session management after login", "OAuth callback handling"],
    "interaction_patterns": ["form_fill", "social_oauth", "link_navigation"]
}}
```

## OUTPUT FORMAT
Return ONLY a valid JSON object following the exact structure shown in the examples above.
Do NOT include any text outside the JSON object.
Find as many business rules as the page's complexity demands — there is no limit."""

        response_text = await self._query(prompt, system_prompt=self.IDENTITY_SYSTEM_PROMPT)
        parsed = self._parse_json_response(response_text)

        if parsed and "page_type" in parsed:
            # Business rules sayısını logla
            rules_count = len(parsed.get("business_rules", []))
            print(f"✅ [Identity] Sayfa tipi: {parsed.get('page_type')} | İş kuralı: {rules_count} | Güven: {parsed.get('confidence', 'N/A')}")
            return parsed

        print("⚠️ [Identity] Parse edilemedi, varsayılan döndürülüyor.")
        return {
            "page_type": "unknown",
            "page_archetype": "Unidentified Page",
            "domain": "unknown",
            "confidence": 0.0,
            "business_rules": [],
            "element_relationships": [],
            "critical_flows": [],
            "risk_areas": [],
            "interaction_patterns": []
        }

    # ═══════════════════════════════════════════════════════════════
    #  KATMAN 3: DİNAMİK VE RİSK ODAKLI SENARYO ÜRETİMİ
    #  (Logical Coverage — Dynamic Test Generation)
    # ═══════════════════════════════════════════════════════════════

    async def generate_test_cases(
        self,
        url: str,
        page_context: str,
        page_identity: Dict[str, Any] = None,
        platform: str = "web"
    ) -> Dict[str, Any]:
        """
        🎯 Mantıksal Kapsama Odaklı Dinamik Test Üretimi.

        Test sayısı SABIT DEĞİLDİR. Sayfanın iş kuralı sayısı ve
        mantıksal derinliği ne kadar test gerektiriyorsa o kadar üretilir.

        Strateji:
          - Her business rule için 1 pozitif + 1 negatif test
          - Risk seviyesi critical olan kurallar önce
          - Semantik selector kullanımı (kırılgan ID'ler yerine)
          - Sayfa tipine özel edge case ve security testleri
        """
        print(f"🤖 [LLM] Dinamik test senaryoları üretiliyor: {url} ({platform})")

        # ── Identity raporunu prompt'a enjekte et ──
        identity_block = ""
        if page_identity and page_identity.get("page_type") != "unknown":
            rules_text = ""
            for i, rule in enumerate(page_identity.get("business_rules", []), 1):
                if isinstance(rule, dict):
                    rules_text += f"  {i}. [{rule.get('risk_level', 'medium').upper()}] {rule.get('rule', '')} (Type: {rule.get('type', 'unknown')})\n"
                elif isinstance(rule, str):
                    rules_text += f"  {i}. {rule}\n"

            relationships_text = ""
            for rel in page_identity.get("element_relationships", []):
                if isinstance(rel, dict):
                    parent = rel.get("parent", "Unknown")
                    children = ", ".join(rel.get("children", []))
                    relationships_text += f"  - {parent} → [{children}]\n"

            flows_text = "\n".join(f"  - {f}" for f in page_identity.get("critical_flows", []))
            risks_text = "\n".join(f"  - {r}" for r in page_identity.get("risk_areas", []))

            identity_block = f"""
## PAGE IDENTITY REPORT (Pre-analyzed)
- **Page Type:** {page_identity.get('page_type', 'unknown')}
- **Page Archetype:** {page_identity.get('page_archetype', 'N/A')}
- **Domain:** {page_identity.get('domain', 'unknown')}
- **Confidence:** {page_identity.get('confidence', 'N/A')}

### Discovered Business Rules:
{rules_text if rules_text else '  (No rules discovered — infer your own from the page context)'}

### Element Relationships:
{relationships_text if relationships_text else '  (No relationships mapped)'}

### Critical User Flows:
{flows_text if flows_text else '  (No flows identified)'}

### Risk Areas:
{risks_text if risks_text else '  (No risk areas identified)'}
"""

        prompt = f"""## MISSION
You are generating test scenarios for an autonomous test execution engine.
The tests you produce will be run by a Playwright-based robot with NO human intervention.
Every test must be precise, executable, and self-contained.

## TARGET
- **URL:** {url}
- **Platform:** {platform}

## RAW PAGE CONTEXT (Detected UI Elements)
{page_context}
{identity_block}

## TEST GENERATION STRATEGY: LOGICAL COVERAGE

### Core Principle: NO FIXED TEST COUNT
Do NOT produce a fixed number of tests. Instead:
- For EACH business rule discovered above, generate:
  • 1 POSITIVE test: The rule is correctly followed → expected success
  • 1 NEGATIVE test: The rule is deliberately violated → expected error/prevention
- Then add page-type-specific edge cases and security checks as the complexity demands.
- A simple login page might produce 8 tests total. A complex checkout might produce 25. Let the LOGIC decide.

### Selector Strategy: SEMANTIC & RESILIENT
NEVER use brittle selectors like `#dynamic-id-x7k2` or `.css-1a2b3c`.
ALWAYS prefer resilient selectors in this priority order:
1. `button:has-text('Submit')` — text-based (best)
2. `input[placeholder='Enter your email']` — attribute-based
3. `[aria-label='Search']` — accessibility-based
4. `[data-testid='login-btn']` — test-id-based
5. `form >> input[type='email']` — structural chaining
6. `.login-form .submit-btn` — semantic class names (last resort)

### Pre-Test Resilience Steps
Every scenario's FIRST steps must handle real-world obstacles:
1. Navigate to the URL
2. Wait for network idle (page fully loaded)
3. Dismiss any cookie consent banners if present
4. Close any promotional popups or newsletter modals if present
Then proceed with the actual test steps.

### Negative Test Philosophy: "THE RULE BREAKER"
When creating negative tests, think like this:
- If the rule says "email must be valid" → type "not-an-email" and verify error
- If the rule says "date B must be after date A" → set date B BEFORE date A and verify prevention
- If the rule says "field is required" → leave it empty, submit, verify error message
- If the rule says "minimum 8 characters" → type only 3 characters, verify rejection

## OUTPUT FORMAT
Return a JSON object with these categories:

```json
{{
    "page_analysis_summary": "One sentence describing what this page is and its core purpose",
    "total_rules_covered": 5,
    "happy_path": [
        {{
            "title": "Descriptive test title tied to a business rule",
            "covers_rule": "The specific business rule this test validates",
            "risk_level": "critical|high|medium|low",
            "steps": [
                {{"action": "navigate", "target": "{url}", "value": "", "expected": "Page loads successfully"}},
                {{"action": "wait", "target": "networkidle", "value": "", "expected": "All resources loaded"}},
                {{"action": "click", "target": "button:has-text('Accept Cookies')", "value": "", "expected": "Cookie banner dismissed if present"}},
                {{"action": "type", "target": "input[placeholder='Email']", "value": "user@example.com", "expected": "Email entered in the field"}},
                {{"action": "click", "target": "button:has-text('Submit')", "value": "", "expected": "Form submitted successfully"}}
            ],
            "expected_outcome": "User sees confirmation message"
        }}
    ],
    "negative_path": [
        {{
            "title": "Verify rejection when [rule is violated]",
            "covers_rule": "The specific business rule being deliberately broken",
            "violation_strategy": "What exactly we are doing wrong on purpose",
            "risk_level": "critical|high|medium|low",
            "steps": [
                {{"action": "navigate", "target": "{url}", "value": "", "expected": "Page loads successfully"}},
                {{"action": "wait", "target": "networkidle", "value": "", "expected": "All resources loaded"}},
                {{"action": "type", "target": "input[placeholder='Email']", "value": "invalid-email", "expected": "Invalid email typed deliberately"}},
                {{"action": "click", "target": "button:has-text('Submit')", "value": "", "expected": "Form submission attempted"}},
                {{"action": "verify", "target": ".error-message", "value": "", "expected": "Error message is displayed for invalid email"}}
            ],
            "expected_outcome": "System prevents action and shows appropriate error"
        }}
    ],
    "edge_cases": [
        {{
            "title": "Edge case description",
            "covers_rule": "Related business rule or general robustness",
            "risk_level": "medium",
            "steps": [...],
            "expected_outcome": "System handles edge case gracefully"
        }}
    ],
    "security_checks": [
        {{
            "title": "Security test description",
            "risk_level": "critical",
            "steps": [...],
            "expected_outcome": "System is protected against this attack vector"
        }}
    ]
}}
```

## CRITICAL REMINDERS
- "action" must be one of: navigate | click | type | verify | wait | scroll | hover | select
- "target" must be a REAL, resilient CSS/text selector — NEVER pseudo-English like "the login button"
- "value" is text to type (for type action) or option to select (for select action), empty string for others
- Steps must be in logical execution order — a robot will run them top to bottom
- Return ONLY valid JSON, no explanation text before or after"""

        response_text = await self._query(prompt, system_prompt=self.TESTGEN_SYSTEM_PROMPT)
        parsed = self._parse_json_response(response_text)

        if parsed:
            # Kaç test üretildiğini logla
            total = sum(
                len(parsed.get(cat, []))
                for cat in ["happy_path", "negative_path", "edge_cases", "security_checks"]
            )
            print(f"✅ [TestGen] Toplam {total} senaryo üretildi (Mantıksal Kapsama)")
            for cat in ["happy_path", "negative_path", "edge_cases", "security_checks"]:
                count = len(parsed.get(cat, []))
                if count > 0:
                    print(f"   → {cat}: {count}")
            return parsed

        print("⚠️ [TestGen] Parse edilemedi, fallback kullanılıyor.")
        return self._get_fallback_cases(url, platform)

    # ═══════════════════════════════════════════════════════════════
    #  GERİYE DÖNÜK UYUMLULUK
    # ═══════════════════════════════════════════════════════════════

    async def generate_test_scenarios(self, app_context: str, platform: str) -> List[str]:
        """Geriye dönük uyumluluk için eski metod (basit liste döndürür)."""
        result = await self.generate_test_cases(
            url=app_context,
            page_context=app_context,
            platform=platform
        )
        steps = []
        for category in result.values():
            if isinstance(category, list):
                for case in category:
                    if isinstance(case, dict) and "steps" in case:
                        steps.extend(case["steps"])
        return steps if steps else [app_context]

    # ═══════════════════════════════════════════════════════════════
    #  HATA KÖK NEDEN ANALİZİ
    # ═══════════════════════════════════════════════════════════════

    async def analyze_error(self, logs: str, screenshot_desc: str) -> Dict[str, Any]:
        """
        🔍 Hata Kök Neden Analizi.
        Logları ve görsel bağlamı birlikte analiz ederek
        hatanın GERÇEK nedenini bulur.
        """
        print("🔍 [LLM] Kök Neden Analizi Başlıyor...")

        prompt = f"""## MISSION
Analyze the following test execution failure and find the TRUE root cause.
Do not stop at the surface-level error — dig deeper.

## ERROR CONTEXT

### Execution Logs (last 1500 chars):
{logs[-1500:]}

### Visual Context (what the screen looks like right now):
{screenshot_desc}

## CHAIN-OF-THOUGHT ANALYSIS
Think through these steps:

1. **Surface Error:** What does the log literally say went wrong?
2. **Visual Correlation:** Does the screenshot match the expected state? If not, what's different?
3. **Hidden Causes:** Could any of these be the real problem?
   - A cookie/consent banner blocking the target element
   - An overlay/modal preventing interaction
   - AJAX content not yet loaded (timing issue)
   - Element exists but is outside viewport (scroll needed)
   - Element selector changed due to dynamic rendering
   - Backend silently rejecting input (no frontend error, but action fails)
   - Localization/encoding issue (special characters in input)
4. **Root Cause:** What is the SINGLE most likely root cause?
5. **Fix:** What specific action would fix this?

## OUTPUT FORMAT
Return ONLY this JSON:
{{
    "surface_error": "What the log literally says",
    "root_cause": "The TRUE underlying reason (may differ from surface error)",
    "root_cause_category": "selector_changed | timing_issue | overlay_blocking | backend_error | validation_error | scroll_needed | encoding_issue | network_error | other",
    "confidence": 0.85,
    "suggestion": "Specific, actionable fix",
    "self_healing_action": "What the executor should try automatically (e.g., 'dismiss_overlay', 'wait_longer', 'scroll_to_element', 'retry_with_alternative_selector')",
    "severity": "Low|Medium|High|Critical",
    "prevention_tip": "How to prevent this in future test design"
}}"""

        response_text = await self._query(prompt, system_prompt=self.ERROR_ANALYSIS_SYSTEM_PROMPT)
        parsed = self._parse_json_response(response_text)

        if parsed and "root_cause" in parsed:
            print(f"✅ [Analiz] Kök neden: {parsed.get('root_cause_category', 'unknown')} | Şiddet: {parsed.get('severity', 'Unknown')}")
            return parsed

        return {
            "surface_error": "Parse Error",
            "root_cause": "LLM response could not be parsed",
            "root_cause_category": "other",
            "confidence": 0.0,
            "suggestion": "Check LLM connectivity and retry",
            "self_healing_action": "retry",
            "severity": "Unknown",
            "raw_response": response_text
        }

    # ═══════════════════════════════════════════════════════════════
    #  FALLBACK TEST CASES
    # ═══════════════════════════════════════════════════════════════

    def _get_fallback_cases(self, url: str, platform: str) -> Dict[str, Any]:
        """API başarısız olunca temel test case'leri döndürür."""
        return {
            "page_analysis_summary": f"Fallback analysis for {url}",
            "total_rules_covered": 0,
            "happy_path": [
                {
                    "title": f"Verify {url} loads successfully",
                    "covers_rule": "Basic page accessibility",
                    "risk_level": "high",
                    "steps": [
                        {"action": "navigate", "target": url, "value": "", "expected": "Page loads"},
                        {"action": "wait", "target": "networkidle", "value": "", "expected": "All resources loaded"},
                        {"action": "verify", "target": "body", "value": "", "expected": "Page body is visible"}
                    ],
                    "expected_outcome": "Page loads without errors"
                }
            ],
            "negative_path": [
                {
                    "title": "Test invalid form submission",
                    "covers_rule": "Form validation",
                    "risk_level": "high",
                    "steps": [
                        {"action": "navigate", "target": url, "value": "", "expected": "Page loads"},
                        {"action": "wait", "target": "networkidle", "value": "", "expected": "All resources loaded"},
                        {"action": "click", "target": "button[type='submit']", "value": "", "expected": "Submit attempted with empty fields"},
                        {"action": "verify", "target": ".error, .alert, [role='alert']", "value": "", "expected": "Validation error displayed"}
                    ],
                    "expected_outcome": "Validation error messages are displayed"
                }
            ],
            "edge_cases": [
                {
                    "title": "Test with special characters in input fields",
                    "covers_rule": "Input sanitization",
                    "risk_level": "medium",
                    "steps": [
                        {"action": "navigate", "target": url, "value": "", "expected": "Page loads"},
                        {"action": "wait", "target": "networkidle", "value": "", "expected": "All resources loaded"},
                        {"action": "type", "target": "input[type='text']", "value": "!@#$%^&*()éàü中文", "expected": "Special characters entered"},
                        {"action": "click", "target": "button[type='submit']", "value": "", "expected": "Form submitted"},
                        {"action": "verify", "target": "body", "value": "", "expected": "Application handles special characters gracefully"}
                    ],
                    "expected_outcome": "Application handles special characters without crashing"
                }
            ],
            "security_checks": [
                {
                    "title": "Basic XSS injection test",
                    "covers_rule": "XSS prevention",
                    "risk_level": "critical",
                    "steps": [
                        {"action": "navigate", "target": url, "value": "", "expected": "Page loads"},
                        {"action": "wait", "target": "networkidle", "value": "", "expected": "All resources loaded"},
                        {"action": "type", "target": "input[type='text']", "value": "<script>alert('xss')</script>", "expected": "XSS payload entered"},
                        {"action": "click", "target": "button[type='submit']", "value": "", "expected": "Form submitted"},
                        {"action": "verify", "target": "body", "value": "", "expected": "Script is not executed, input is sanitized"}
                    ],
                    "expected_outcome": "XSS payload is sanitized, no script execution"
                }
            ]
        }
