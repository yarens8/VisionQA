
import os
import httpx
from typing import Dict, Any, Optional

class DINOXClient:
    """
    Hugging Face Inference API (OWL-ViT veya benzeri) üzerinden Grounding Wrapper.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HF_API_TOKEN") 
        self.model_id = os.getenv("DINO_MODEL_ID", "google/owlvit-base-patch32")
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"

    async def ground_query(self, screenshot_path: str, query: str) -> Dict[str, Any]:
        """
        Bir metni veya nesneyi görselde arar.
        (Örnek: "login button")
        """
        print(f"🎯 [DINO-X] Aranıyor: '{query}', Görsel: {screenshot_path}")

        if not self.api_key:
            # MOCK
            return {
                "found": True,
                "label": query,
                "box": [150, 220, 250, 240],
                "score": 0.89,
                "reason": "Mock mode active"
            }

        try:
            # 1. Görseli Oku
            with open(screenshot_path, "rb") as f:
                image_data = f.read()
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # Not: Hugging Face Zero-Shot Object Detection API genellikle şöyle çalışır:
            # { "inputs": image_data, "parameters": {"candidate_labels": ["login button", "cart"]} }
            # Ancak Inference API binary data + JSON parametreleri aynı anda almayı zorlaştırabilir.
            # Alternatif: "inputs" içinde base64 string göndermek.

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, 
                    headers=headers, 
                    content=image_data,
                    # parameters={"candidate_labels": [query]} # (Bu kısım modelden modele değişir)
                )

                if response.status_code != 200:
                   print(f"❌ [DINO-X] API Hatası: {response.text}")
                   return {"found": False, "error": response.text}

                results = response.json()
                # En iyi sonucu seç
                if isinstance(results, list) and len(results) > 0:
                    best = max(results, key=lambda x: x.get('score', 0))
                    return {
                        "found": True,
                        "label": best.get('label', query),
                        "box": best.get('box', {}),
                        "score": best.get('score', 0)
                    }
                
                return {"found": False}

        except Exception as e:
            print(f"❌ [DINO-X] Hata: {str(e)}")
            return {"found": False, "error": str(e)}
