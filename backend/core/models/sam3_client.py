
import os
import base64
import requests
from typing import List, Dict, Any, Optional

class SAM3Client:
    """
    Hugging Face Inference API üzerinden Segmentation Modeli (SAM) Wrapper.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_id: Optional[str] = None):
        # Env veya parametreden al
        self.api_key = api_key or os.getenv("HF_API_TOKEN")
        self.model_id = model_id or os.getenv("SAM_MODEL_ID", "facebook/sam-vit-base")
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        
        if not self.api_key:
            print("⚠️ [SAM3] Uyarı: HF_API_TOKEN bulunamadı. Mock modunda çalışacak.")

    def detect_ui_elements(self, screenshot_path: str, platform: str = "web") -> List[Dict[str, Any]]:
        """
        Görseli Hugging Face API'ye gönderir ve segmentasyon maskelerini alır.
        """
        print(f"🤖 [SAM3] Analiz ediliyor ({self.model_id}): {screenshot_path}")

        if not self.api_key:
             # MOCK RESPONSE (API Key yoksa)
            return [
                {"label": "button", "box": [100, 200, 300, 250], "score": 0.98},
                {"label": "input", "box": [100, 100, 300, 150], "score": 0.95}
            ]

        # 1. Görseli Base64 yap
        try:
            with open(screenshot_path, "rb") as image_file:
                image_data = image_file.read() # Binary veri gönderilebilir
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # 2. API İsteği Gönder (Binary olarak resim gönder)
            # Not: SAM modeli binary veri kabul eder
            response = requests.post(self.api_url, headers=headers, data=image_data)
            
            if response.status_code != 200:
                print(f"❌ [SAM3] API Hatası ({response.status_code}): {response.text}")
                return []
                
            result = response.json()
            # Hugging Face SAM çıktısı genelde karmaşıktır (maskeler).
            # Şimdilik basit obje tespiti (DETR) gibi varsayalım, SAM çıktısını işlemek zordur.
            # (Gerçek entegrasyonda mask -> box dönüşümü gerekir)
            
            print(f"✅ [SAM3] Başarılı! {len(result)} nesne bulundu.")
            return result

        except Exception as e:
            print(f"❌ [SAM3] Hata: {str(e)}")
            return []
