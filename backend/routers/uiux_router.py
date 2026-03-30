from fastapi import APIRouter, HTTPException

import schemas
from core.uiux.engine import UiuxEngine


router = APIRouter(prefix="/uiux", tags=["uiux"])
engine = UiuxEngine()


@router.post("/analyze-image", response_model=schemas.UiuxAnalysisResponse)
async def analyze_uiux_image(request: schemas.UiuxAnalysisRequest):
    try:
        return engine.analyze_image(
            image_base64=request.image_base64,
            platform=request.platform,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"UI/UX analysis failed: {exc}") from exc

