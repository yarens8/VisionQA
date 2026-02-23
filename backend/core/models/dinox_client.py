
import os
import httpx
import json
import base64
import asyncio
from typing import List, Dict, Any, Optional

class DINOXClient:
    """
    👁️ VisionQA — Grounding DINO (DINO-X) Semantik Tahminleyici
    Hugging Face Inference API üzerinden çalışır.
    
    GELİŞTİRME: Model yüklenme (loading) hatalarını yönetir ve Türkçe desteği barındırır.
    """

    # Global engel çözücü için kapsamlı prompt (EN + TR)
    OBSTACLES_PROMPT = "accept cookies, reject cookies, close button, dismiss icon, newsletter popup, allow, kadın, erkek, woman, man, gender selection, kabul et, reddet, kapat, onaylıyorum, anladım"
    DEFAULT_PROMPT = "button, input, link, icon, text block, dropdown, checkbox, radio button"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HF_API_TOKEN") 
        # Daha stabil bir model seçiyoruz (OWL-ViT bazen HF'de daha stabil olabiliyor, 
        # ama biz Grounding DINO'da ısrarcıysak retry eklemeliyiz)
        self.model_id = os.getenv("DINO_MODEL_ID", "IDEA-Research/grounding-dino-base") 
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        
        if not self.api_key:
            print("👁️ [DINO-X] UYARI: API Key yok, MOCK modunda çalışacak.")

    async def _query_api(self, payload: Dict[str, Any], retries: int = 3) -> Any:
        """HF API'ye güvenli sorgu atar, model yükleniyorsa bekler."""
        if not self.api_key:
            return None

        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient() as client:
            for i in range(retries):
                try:
                    response = await client.post(
                        self.api_url, 
                        headers=headers, 
                        json=payload,
                        timeout=45.0
                    )
                    
                    res_json = response.json()
                    
                    # Model hala yükleniyorsa bekle (HF spesifik hata)
                    if isinstance(res_json, dict) and "error" in res_json:
                        err = res_json.get("error", "").lower()
                        if "loading" in err:
                            wait_time = res_json.get("estimated_time", 20)
                            print(f"⏳ [DINO-X] Model yükleniyor, {wait_time:.1f}s bekleniyor... (Deneme {i+1}/{retries})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            print(f"❌ [DINO-X] API Hatası: {res_json.get('error')}")
                            return None
                    
                    return res_json
                except Exception as e:
                    print(f"⚠️ [DINO-X] İstek Hatası: {e}")
                    await asyncio.sleep(2)
        return None

    async def detect_elements(self, screenshot_path: str, prompt: str = None) -> List[Dict[str, Any]]:
        """Elementleri tespit eder."""
        prompt = prompt or self.DEFAULT_PROMPT
        if not self.api_key:
            return self._get_mock_elements(prompt)

        try:
            with open(screenshot_path, "rb") as f:
                image_data = f.read()
            
            # Grounding DINO formatı: inputs içinde 'image' (base64) ve 'text' (prompt)
            payload = {
                "inputs": {
                    "image": base64.b64encode(image_data).decode("utf-8"),
                    "text": prompt # Grounding DINO 'text' parametresiyle çalışır
                }
            }

            results = await self._query_api(payload)
            
            formatted_results = []
            if isinstance(results, list):
                for item in results:
                    formatted_results.append({
                        "label": item.get("label", "unknown"),
                        "box": item.get("box", {}),
                        "score": item.get("score", 0)
                    })
            
            return formatted_results

        except Exception as e:
            print(f"❌ [DINO-X] Beklenmedik Hata: {str(e)}")
            return []

    async def get_world_view(self, screenshot_path: str) -> str:
        """LLM için World View üretir."""
        elements = await self.detect_elements(screenshot_path)
        if not elements:
            return "No UI elements detected via DINO-X (API might be loading or no matches found)."

        world_view = "### SEUMANTIC WORLD VIEW (Detected via DINO-X)\n"
        for i, elem in enumerate(elements, 1):
            label = elem.get("label", "element")
            box = elem.get("box", [])
            score = elem.get("score", 0)
            world_view += f"{i}. [{label}] at {box} (confidence: {score:.2f})\n"
        
        return world_view

    def _get_mock_elements(self, prompt: str) -> List[Dict[str, Any]]:
        """API Key yoksa çalışan mock sistemi (geliştirildi)."""
        mock_results = []
        if "accept" in prompt or "kabul" in prompt:
            # Tipik çerez banner butonu (Mock)
            mock_results.append({"label": "kabul_et_button", "box": {"xmin": 600, "ymin": 800, "xmax": 800, "ymax": 850}, "score": 0.95})
        
        if "input" in prompt or "search" in prompt:
            mock_results.append({"label": "search_box", "box": {"xmin": 300, "ymin": 150, "xmax": 700, "ymax": 200}, "score": 0.92})
            
        return mock_results
