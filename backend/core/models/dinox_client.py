
import os
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class DINOXClient:
    """
    👁️ VisionQA — Grounding DINO (Lokal) Görsel Element Tespit Motoru

    Sayfa screenshot'ını alır, üzerindeki UI elementlerini (buton, input, link vb.)
    tespit eder ve etiketli bounding box'lar döndürür.

    Mimari:
      - Model ağırlıkları ilk çalışmada HuggingFace'den indirilir (~700MB)
      - Sonraki çalışmalarda cache'den okunur (internet gerekmez)
      - Model bellekte tutulur, her analiz ~1-2 saniye sürer
      - Proje bittiğinde DINO-X Cloud API'ye geçiş tek satır değişikliğidir

    Kullanım:
        client = DINOXClient()
        elements = await client.detect_elements("screenshot.png")
        # [{"label": "button", "score": 0.85, "box": [100, 200, 300, 250]}, ...]
    """

    # UI element tespiti için varsayılan prompt
    DEFAULT_PROMPT = "button. input field. text field. link. logo. icon. navigation menu. search bar. dropdown. checkbox. image. form. header. footer."

    # Global engel tespiti için prompt (çerez banner'ları, popup'lar vb.)
    OBSTACLES_PROMPT = "cookie banner. accept button. reject button. close button. popup. modal. overlay. newsletter popup."

    _instance: Optional["DINOXClient"] = None
    _model = None
    _processor = None

    def __init__(self):
        self.model_id = os.getenv("DINO_MODEL_ID", "IDEA-Research/grounding-dino-base")
        # torch sadece model kullanılırken import edilecek
        self.device = "cpu"  # Lazy: torch yoksa default cpu

        # Model'i sadece 1 kere yükle (Singleton pattern)
        if DINOXClient._model is None:
            self._load_model()
        
        self.model = DINOXClient._model
        self.processor = DINOXClient._processor

    def _load_model(self):
        """Model ağırlıklarını yükler (sadece ilk seferde)."""
        try:
            import torch
            from PIL import Image as PILImage  # noqa: F401
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            raise RuntimeError(
                "DINO modeli için 'torch' ve 'pillow' kütüphaneleri gerekli. "
                "Lütfen `pip install torch torchvision pillow` çalıştırın."
            )
        print(f"👁️ [Grounding DINO] Model yükleniyor: {self.model_id}")
        print(f"   Cihaz: {self.device}")
        start = time.time()

        from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

        DINOXClient._processor = AutoProcessor.from_pretrained(self.model_id)
        DINOXClient._model = AutoModelForZeroShotObjectDetection.from_pretrained(
            self.model_id
        ).to(self.device)

        elapsed = time.time() - start
        print(f"✅ [Grounding DINO] Model hazır! ({elapsed:.1f} saniye)")

    async def detect_elements(
        self,
        screenshot_path: str,
        prompt: str = None,
        box_threshold: float = 0.25,
        text_threshold: float = 0.20
    ) -> List[Dict[str, Any]]:
        """
        Screenshot üzerindeki UI elementlerini tespit eder.

        Args:
            screenshot_path: Analiz edilecek görsel dosya yolu
            prompt: Aranacak element türleri (nokta ile ayrılmış)
            box_threshold: Minimum kutu güven skoru (0-1)
            text_threshold: Minimum metin eşleşme skoru (0-1)

        Returns:
            [{"label": "button", "score": 0.85, "box": [x1, y1, x2, y2]}, ...]
        """
        prompt = prompt or self.DEFAULT_PROMPT
        print(f"👁️ [Grounding DINO] Analiz ediliyor: {screenshot_path}")

        try:
            import torch
            from PIL import Image
            # Görseli aç
            image = Image.open(screenshot_path).convert("RGB")
            w, h = image.size

            # Prompt'u küçük harfe çevir (Grounding DINO gereksinimi)
            prompt_lower = prompt.lower()

            # Model'e gönder
            inputs = self.processor(
                images=image,
                text=prompt_lower,
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)

            # Sonuçları işle
            elements = self._post_process(
                outputs, inputs, image, prompt_lower,
                box_threshold, text_threshold
            )

            print(f"✅ [Grounding DINO] {len(elements)} element bulundu!")
            return elements

        except Exception as e:
            print(f"❌ [Grounding DINO] Hata: {str(e)}")
            return []

    async def detect_obstacles(self, screenshot_path: str) -> List[Dict[str, Any]]:
        """
        Sayfadaki engelleri (çerez banner, popup vb.) tespit eder.
        SelfHealingExecutor tarafından kullanılır.
        """
        return await self.detect_elements(
            screenshot_path,
            prompt=self.OBSTACLES_PROMPT,
            box_threshold=0.30,
            text_threshold=0.25
        )

    def _post_process(
        self,
        outputs,
        inputs,
        image: Any,
        prompt: str,
        box_threshold: float,
        text_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Model çıktısını etiketli element listesine dönüştürür.
        """
        w, h = image.size
        logits = outputs.logits.sigmoid()[0]  # (num_queries, num_tokens)
        boxes = outputs.pred_boxes[0]          # (num_queries, 4)

        # Her kutu için en yüksek skoru bul
        max_scores = logits.max(dim=-1)
        mask = max_scores.values > box_threshold

        filtered_boxes = boxes[mask]
        filtered_logits = logits[mask]
        filtered_scores = max_scores.values[mask]

        # Prompt'taki label'ları çıkart
        labels = [l.strip() for l in prompt.split('.') if l.strip()]

        # Tokenizer ile her label'ın token pozisyonlarını hesapla
        input_ids = inputs.input_ids[0].tolist()
        tokenizer = self.processor.tokenizer
        
        label_token_map = {}
        for label in labels:
            label_tokens = tokenizer.encode(label, add_special_tokens=False)
            for j in range(len(input_ids) - len(label_tokens) + 1):
                if input_ids[j:j + len(label_tokens)] == label_tokens:
                    label_token_map[label] = list(range(j, j + len(label_tokens)))
                    break

        # Sonuçları oluştur
        elements = []
        for i in range(len(filtered_boxes)):
            score = filtered_scores[i].item()
            box_raw = filtered_boxes[i].tolist()

            # Normalize koordinatları piksel değerlerine çevir
            cx, cy, bw, bh = box_raw
            x1 = round((cx - bw / 2) * w, 1)
            y1 = round((cy - bh / 2) * h, 1)
            x2 = round((cx + bw / 2) * w, 1)
            y2 = round((cy + bh / 2) * h, 1)

            # En iyi eşleşen label'ı bul
            token_scores = filtered_logits[i]
            best_label = "unknown"
            best_label_score = 0

            for label, positions in label_token_map.items():
                if positions:
                    avg_score = token_scores[positions].mean().item()
                    if avg_score > best_label_score and avg_score > text_threshold:
                        best_label_score = avg_score
                        best_label = label

            elements.append({
                "label": best_label,
                "score": round(score, 3),
                "box": [x1, y1, x2, y2]
            })

        # Skora göre sırala (en güvenli önce)
        elements.sort(key=lambda x: -x["score"])

        return elements

    async def get_world_view(self, screenshot_path: str) -> str:
        """LLM için World View metni üretir."""
        elements = await self.detect_elements(screenshot_path)
        if not elements:
            return "No UI elements detected via Grounding DINO."

        lines = ["### VISUAL WORLD VIEW (Detected via Grounding DINO)"]
        for i, elem in enumerate(elements, 1):
            label = elem.get("label", "element")
            box = elem.get("box", [])
            score = elem.get("score", 0)
            lines.append(f"{i}. [{label}] at {box} (confidence: {score:.2f})")

        return "\n".join(lines)
