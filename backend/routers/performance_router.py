from fastapi import APIRouter, HTTPException

from core.performance.engine import PerformanceEngine
from schemas import PerformanceAnalysisResponse, PerformanceAnalyzeRequest

router = APIRouter(prefix="/performance", tags=["performance"])


@router.post("/analyze", response_model=PerformanceAnalysisResponse)
async def analyze_performance(request: PerformanceAnalyzeRequest):
    if not request.url and not request.api_url and not (request.db_connection_string and request.db_query):
        raise HTTPException(status_code=400, detail="At least one target (url, api_url, or db query) is required.")

    engine = PerformanceEngine()
    return await engine.analyze(
        url=request.url,
        api_url=request.api_url,
        api_method=request.api_method,
        db_connection_string=request.db_connection_string,
        db_query=request.db_query,
        sample_api_runs=request.sample_api_runs,
        platform=request.platform,
    )
