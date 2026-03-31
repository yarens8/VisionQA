from fastapi import APIRouter, HTTPException

from core.mobile.engine import MobileAnalysisEngine
from schemas import MobileAnalysisRequest, MobileAnalysisResponse

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.post("/analyze", response_model=MobileAnalysisResponse)
def analyze_mobile(request: MobileAnalysisRequest):
    if not request.image_base64 and not request.element_metadata:
        raise HTTPException(
            status_code=400,
            detail="Mobil analiz icin screenshot veya element metadata gereklidir.",
        )

    engine = MobileAnalysisEngine()
    return engine.analyze(
        platform=request.platform,
        screen_name=request.screen_name,
        image_base64=request.image_base64,
        element_metadata=[item.model_dump() for item in request.element_metadata],
    )
