
import os
import httpx
import json
import re
from typing import List, Dict, Any, Optional

class LLMClient:
    """
    Hugging Face Inference API üzerinden LLM (Mistral/Llama) Wrapper.
    Görevi: Test senaryosu üretmek, hataları analiz etmek, çözüm önermek.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HF_API_TOKEN")
        # Mistral-7B Instruct v0.2 (Çok iyi talimat takip eder)
        self.model_id = os.getenv("LLM_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.2")
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"

    async def _query_hf(self, prompt: str) -> str:
        """Hugging Face API'ye ham prompt gönderir."""
        if not self.api_key:
            print("⚠️ [LLM] API Key yok! Mock data dönüyor.")
            return "MOCK: Lütfen .env dosyasına HF_API_TOKEN ekleyin."

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "inputs": f"<s>[INST] {prompt} [/INST]", # Mistral Prompt Formatı
            "parameters": {
                "max_new_tokens": 512,
                "temperature": 0.7,
                "return_full_text": False
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.api_url, headers=headers, json=payload, timeout=30.0)
                if response.status_code != 200:
                    print(f"❌ [LLM] API Hatası ({response.status_code}): {response.text}")
                    return ""
                
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "").strip()
                return ""
            except Exception as e:
                print(f"❌ [LLM] Bağlantı Hatası: {str(e)}")
                return ""

    async def generate_test_scenarios(self, app_context: str, platform: str) -> List[str]:
        """
        Uygulama tanımına göre test adımları üretir.
        
        Args:
            app_context: "E-ticaret sitesi, kullanıcı login olup sepeti onaylamalı."
            platform: "web" | "mobile"
        """
        print(f"🤖 [LLM] Senaryo Düşünülüyor: {app_context} ({platform})")
        
        prompt = f"""
        You are a Senior QA Automation Engineer.
        Generate a chronological list of test steps for the following application context.
        Platform: {platform}
        Context: {app_context}

        Rules:
        1. Return ONLY the list of steps.
        2. Do not include explanations.
        3. Each step should be actionable (e.g., "Click 'Login'", "Type username").
        4. Format as a numbered list.
        """

        response_text = await self._query_hf(prompt)
        
        # Basit parse (Numaralı listeyi array'e çevir)
        steps = []
        for line in response_text.split('\n'):
            line = line.strip()
            # "1. Adım" veya "- Adım" formatını yakala
            if re.match(r'^(\d+\.|-)\s+', line):
                steps.append(line)
        
        if not steps:
            # Fallback (Eğer parse edemezse ham metni döndür)
            return [response_text] if response_text else ["Error: No scenario generated."]
            
        print(f"✅ [LLM] {len(steps)} adım üretildi.")
        return steps

    async def analyze_error(self, logs: str, screenshot_desc: str) -> Dict[str, Any]:
        """
        Hata loglarını ve ekran durumunu analiz eder.
        """
        print(f"🔍 [LLM] Hata Analizi Başlıyor...")
        
        prompt = f"""
        You are an AI Debugging Assistant. Analyze the following error.
        
        Error Logs:
        {logs[-500:]}  # Son 500 karakteri al
        
        Visual Context (Screenshot Description):
        {screenshot_desc}

        Task:
        1. Identify the Root Cause.
        2. Suggest a fix.
        3. Estimate severity (Low/Medium/High/Critical).

        Return ONLY a JSON object with keys: "root_cause", "suggestion", "severity".
        """

        response_text = await self._query_hf(prompt)
        
        # JSON'ı ayıkla
        try:
            # Bazen LLM "Here is the JSON:" diye başlar, sadece {...} kısmını alalım.
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            else:
                return {"root_cause": "Parsing Error", "raw_response": response_text}
        except:
            return {"root_cause": "JSON Parsing Failed", "raw_response": response_text}
