import os
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


class SAM3Client:
    """
    VisionQA SAM3 visual concept segmentation client.

    The client uses Hugging Face Transformers' Sam3Model/Sam3Processor when
    they are installed. Model loading is lazy at object construction time so
    CI can import this module without downloading the model.
    """

    DEFAULT_PROMPT = (
        "button. input field. text field. link. logo. icon. navigation menu. "
        "search bar. dropdown. checkbox. image. form. header. footer."
    )
    OBSTACLES_PROMPT = (
        "cookie banner. accept button. reject button. close button. popup. "
        "modal. overlay. newsletter popup."
    )

    _model = None
    _processor = None

    def __init__(self):
        self.model_id = os.getenv("SAM3_MODEL_ID", "facebook/sam3")
        self.hf_token = (
            os.getenv("HF_TOKEN")
            or os.getenv("HUGGINGFACE_HUB_TOKEN")
            or os.getenv("HF_API_TOKEN")
        )
        self.device = "cpu"
        self.last_error: Optional[str] = None
        if SAM3Client._model is None:
            self._load_model()
        self.model = SAM3Client._model
        self.processor = SAM3Client._processor

    def _load_model(self):
        try:
            import torch
            from transformers import Sam3Model, Sam3Processor
        except Exception as exc:
            raise RuntimeError(
                "SAM3 icin Transformers Sam3Model/Sam3Processor yuklenemedi. "
                "requirements.txt icindeki transformers ve scikit-learn surumlerini kurun."
            ) from exc

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"👁️ [SAM3] Model yukleniyor: {self.model_id}")
        print(f"   Cihaz: {self.device}")
        start = time.time()

        load_kwargs = {"token": self.hf_token} if self.hf_token else {}
        try:
            SAM3Client._processor = Sam3Processor.from_pretrained(self.model_id, **load_kwargs)
            SAM3Client._model = Sam3Model.from_pretrained(self.model_id, **load_kwargs).to(self.device)
        except Exception as exc:
            message = str(exc)
            if "gated repo" in message.lower() or "401" in message:
                raise RuntimeError(
                    "SAM3 modeli Hugging Face gated repo olarak korunuyor. "
                    "facebook/sam3 erisimi olan bir hesapla `huggingface-cli login` yapin "
                    "veya HF_TOKEN/HUGGINGFACE_HUB_TOKEN ortam degiskenini ayarlayin."
                ) from exc
            raise
        SAM3Client._model.eval()

        elapsed = time.time() - start
        print(f"✅ [SAM3] Model hazir! ({elapsed:.1f} saniye)")

    async def detect_elements(
        self,
        screenshot_path: str,
        prompt: Optional[str] = None,
        box_threshold: float = 0.35,
        mask_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        prompt = prompt or self.DEFAULT_PROMPT
        labels = self._labels_from_prompt(prompt)
        self.last_error = None
        print(f"👁️ [SAM3] Analiz ediliyor: {screenshot_path} ({len(labels)} concept)")

        try:
            import torch
            from PIL import Image

            image = Image.open(screenshot_path).convert("RGB")
            all_elements: List[Dict[str, Any]] = []

            for label in labels:
                inputs = self.processor(
                    images=image,
                    text=label,
                    return_tensors="pt",
                ).to(self.device)

                with torch.no_grad():
                    outputs = self.model(**inputs)

                results = self.processor.post_process_instance_segmentation(
                    outputs,
                    threshold=box_threshold,
                    mask_threshold=mask_threshold,
                    target_sizes=inputs.get("original_sizes").tolist(),
                )[0]
                all_elements.extend(self._to_elements(label, results))

            elements = self._dedupe_elements(all_elements)
            elements.sort(key=lambda item: -item.get("score", 0))
            print(f"✅ [SAM3] {len(elements)} element bulundu!")
            return elements
        except Exception as exc:
            self.last_error = str(exc)
            print(f"❌ [SAM3] Hata: {exc}")
            return []

    async def detect_obstacles(self, screenshot_path: str) -> List[Dict[str, Any]]:
        return await self.detect_elements(
            screenshot_path,
            prompt=self.OBSTACLES_PROMPT,
            box_threshold=0.40,
            mask_threshold=0.5,
        )

    async def get_world_view(self, screenshot_path: str) -> str:
        elements = await self.detect_elements(screenshot_path)
        if not elements:
            return "No UI elements detected via SAM3."

        lines = ["### VISUAL WORLD VIEW (Detected via SAM3)"]
        for i, elem in enumerate(elements, 1):
            label = elem.get("label", "element")
            box = elem.get("box", [])
            score = elem.get("score", 0)
            lines.append(f"{i}. [{label}] at {box} (confidence: {score:.2f})")
        return "\n".join(lines)

    def _labels_from_prompt(self, prompt: str) -> List[str]:
        labels = [part.strip().lower() for part in prompt.split(".") if part.strip()]
        return labels or ["button"]

    def _to_elements(self, label: str, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        boxes = results.get("boxes", [])
        scores = results.get("scores", [])
        masks = results.get("masks", [])
        elements: List[Dict[str, Any]] = []

        for idx, box in enumerate(boxes):
            box_values = self._tensor_to_list(box)
            if len(box_values) != 4:
                continue
            score = self._tensor_to_float(scores[idx]) if idx < len(scores) else 0.0
            element: Dict[str, Any] = {
                "label": label,
                "score": round(score, 3),
                "box": [round(float(value), 1) for value in box_values],
                "source": "sam3",
            }
            if idx < len(masks):
                element["mask_area"] = self._mask_area(masks[idx])
            elements.append(element)
        return elements

    def _dedupe_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        for element in elements:
            box = element.get("box", [])
            if len(box) != 4:
                continue
            duplicate = False
            for existing in deduped:
                if self._iou(box, existing.get("box", [])) > 0.85:
                    duplicate = True
                    if element.get("score", 0) > existing.get("score", 0):
                        existing.update(element)
                    break
            if not duplicate:
                deduped.append(element)
        return deduped

    def _iou(self, box_a: List[float], box_b: List[float]) -> float:
        if len(box_a) != 4 or len(box_b) != 4:
            return 0.0
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
        union = area_a + area_b - inter_area
        return inter_area / union if union else 0.0

    def _tensor_to_list(self, value: Any) -> List[float]:
        if hasattr(value, "detach"):
            value = value.detach().cpu().tolist()
        elif hasattr(value, "tolist"):
            value = value.tolist()
        return list(value) if isinstance(value, (list, tuple)) else []

    def _tensor_to_float(self, value: Any) -> float:
        if hasattr(value, "detach"):
            return float(value.detach().cpu().item())
        if hasattr(value, "item"):
            return float(value.item())
        return float(value)

    def _mask_area(self, mask: Any) -> int:
        if hasattr(mask, "detach"):
            return int(mask.detach().cpu().sum().item())
        if hasattr(mask, "sum"):
            return int(mask.sum())
        return 0
