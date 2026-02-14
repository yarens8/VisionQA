
from typing import List, Dict, Any
from core.models.llm_client import LLMClient
from core.models.sam3_client import SAM3Client # (İleride görsel analiz için)
# from executors.web.web_executor import WebExecutor

class AICaseGenerator:
    """
    AI tabanlı Test Case Üretici
    
    Akış:
    1. URL al.
    2. (Opsiyonel) Ekran görüntüsü al ve analiz et.
    3. LLM'e sor: "Bu sayfada hangi test senaryoları koşulmalı?"
    4. Test Case listesi döndür.
    """
    
    def __init__(self):
        self.llm = LLMClient()
        # self.sam = SAM3Client()
        # self.executor = WebExecutor()

    async def generate_cases_from_url(self, url: str, platform: str = "web") -> List[Dict[str, Any]]:
        """
        Verilen URL için test senaryoları üretir.
        """
        print(f"🧠 [AI-Generator] Analiz ediliyor: {url}")
        
        # 1. LLM'e Context Verelim
        # (F-string içinde süslü parantezleri escape edelim: {{ }})
        prompt = f"""
        You are a QA Automation Architect.
        I want you to generate test cases for a web application based on this URL: {url}
        Assume this is a standard e-commerce or SaaS platform.
        
        Your Task:
        Generate 3 critical test scenarios (Test Cases).
        For each case, list the step-by-step actions (Test Steps).
        
        Format the output as a valid JSON list of objects:
        [
            {{
                "title": "Case Title",
                "description": "Case Description",
                "priority": "high",
                "steps": [
                    {{"order": 1, "action": "navigate", "target": "{url}", "expected": "Page loads"}},
                    {{"order": 2, "action": "click", "target": "login_btn", "expected": "Redirect"}}
                ]
            }}
        ]
        
        IMPORTANT: Return ONLY the JSON. Do not include 'Here is the JSON' or markdown code blocks.
        """
        
        # 2. LLM'den Cevap Al
        response_text = await self.llm._query_hf(prompt)
        # Debug için yazdıralım
        print(f"🤖 [LLM-Raw]: {response_text[:100]}...")

        # 3. JSON Parse Et
        import json
        import re
        
        try:
            # Markdown code block temizliği (```json ... ```)
            cleaned_text = re.sub(r'```json\s*|\s*```', '', response_text).strip()
            
            # Köşeli parantezleri bul [...]
            match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                cases = json.loads(json_str)
                print(f"✅ [AI-Generator] {len(cases)} test case başarıyla parse edildi.")
                return cases
            else:
                print("❌ [AI-Generator] JSON formatı bulunamadı. Ham metin döndürülüyor.")
                # Fallback: Eğer JSON yoksa boş dön veya mock dön
                return []
                
        except Exception as e:
            print(f"❌ [AI-Generator] Parse Hatası: {str(e)}")
            return []

    async def generate_steps_from_description(self, description: str) -> List[Dict[str, Any]]:
        """
        Kullanıcının girdiği bir cümleden ("Login ol ve sepete git") adımları üretir.
        """
        # (Benzer mantıkla burası da doldurulabilir)
        pass
