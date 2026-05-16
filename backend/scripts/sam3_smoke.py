import argparse
import asyncio
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.models.sam3_client import SAM3Client


def _create_sample_ui(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (640, 360), "#f8fafc")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    draw.rounded_rectangle((40, 40, 600, 320), radius=16, fill="#ffffff", outline="#cbd5e1", width=2)
    draw.text((72, 72), "VisionQA Login", fill="#0f172a", font=font)
    draw.rounded_rectangle((72, 120, 568, 164), radius=8, fill="#eef2ff", outline="#64748b", width=2)
    draw.text((92, 136), "email@example.com", fill="#334155", font=font)
    draw.rounded_rectangle((72, 186, 568, 230), radius=8, fill="#eef2ff", outline="#64748b", width=2)
    draw.text((92, 202), "password", fill="#334155", font=font)
    draw.rounded_rectangle((220, 260, 420, 306), radius=10, fill="#2563eb", outline="#1d4ed8", width=2)
    draw.text((294, 276), "Login", fill="#ffffff", font=font)

    image.save(path)


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run a real SAM3 smoke analysis.")
    parser.add_argument("--image", default="storage/sam3_smoke/sample_ui.png")
    parser.add_argument("--prompt", default="button. input field. text field.")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        _create_sample_ui(image_path)

    try:
        client = SAM3Client()
    except Exception as exc:
        result = {
            "image": str(image_path),
            "model_id": "facebook/sam3",
            "status": "blocked",
            "reason": str(exc),
            "hint": "Hugging Face hesabinda facebook/sam3 erisimini acip HF_TOKEN ayarlayin.",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    elements = await client.detect_elements(str(image_path), prompt=args.prompt)

    result = {
        "image": str(image_path),
        "model_id": client.model_id,
        "device": client.device,
        "status": "ok" if not client.last_error else "failed",
        "last_error": client.last_error,
        "element_count": len(elements),
        "elements": elements[:10],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if client.last_error else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
