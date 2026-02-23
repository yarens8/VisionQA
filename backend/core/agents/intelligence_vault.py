
from typing import Dict, Any, Optional

class IntelligenceVault:
    """
    🔐 VisionQA — Akıllı Bilgi Kasası (Intelligence Vault)
    
    Test senaryolarında (özellikle pozitif testlerde) kullanılacak 
    doğru kullanıcı verilerini tutar. LLM bu verileri kullanarak
    form doldurma ve seçim (cinsiyet vb.) kararlarını verir.
    """
    
    def __init__(self, profile_data: Optional[Dict[str, Any]] = None):
        # Varsayılan profil (Eğer kullanıcı sağlamazsa)
        self.data = profile_data or {
            "full_name": "Test User",
            "email": "test@visionqa.ai",
            "gender": "kadın", # 'kadın' veya 'erkek'
            "phone": "5550001122",
            "username": "standard_user",
            "password": "secret_password"
        }

    def get_value(self, key: str) -> Any:
        return self.data.get(key)

    def get_all(self) -> Dict[str, Any]:
        return self.data

    def summarize_for_llm(self) -> str:
        """LLM'in anlayacağı kısa bir özet döner."""
        summary = "Available User Context (The Truth):\n"
        for key, val in self.data.items():
            summary += f"- {key}: {val}\n"
        return summary
