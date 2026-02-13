
from typing import List, Dict, Any, Optional

class LLMClient:
    """
    LLM (Large Language Model) Wrapper - OpenAI / Claude / Ollama
    Görevi: Senaryo üretmek, hata analizi yapmak, rapor oluşturmak.
    """
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key
        # self.endpoint = ...

    async def generate_test_scenarios(self, context: str, platform: str) -> List[str]:
        """
        Girdiğiniz uygulama tanımına göre test senaryoları üretir.
        """
        print(f"🤖 [LLM-{self.provider}] Senaryo üretiliyor... Context: {context}")
        
        # MOCK - E-Ticaret sitesi için
        if "ecommerce" in context.lower():
            return [
                "1. Anasayfayı aç",
                "2. 'Login' butonuna tıkla",
                "3. Geçerli kullanıcı adı ve şifre gir",
                "4. 'Giriş Yap'a bas",
                "5. Sepete ürün ekle",
            ]
        
        return ["1. Uygulamayı aç", "2. Ana ekranı doğrula"]

    async def analyze_error(self, logs: str, screenshot_desc: str) -> Dict[str, Any]:
        """
        Hata mesajlarını ve ekranı analiz eder.
        Returns:
            Dict: Hata nedeni ve çözüm önerisi.
        """
        print(f"🔍 [LLM] Hata Analizi: {logs[:50]}...")
        
        return {
            "root_cause": "TimeoutException - Element not found within 30s.",
            "suggestion": "Increase wait time or check if element ID changed.",
            "severity": "High"
        }
