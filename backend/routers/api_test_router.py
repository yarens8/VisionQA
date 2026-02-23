
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from database import get_db
from executors.api.api_executor import APIExecutor
import json

router = APIRouter(prefix="/api-test", tags=["api-test"])

class APIRequestSchema(BaseModel):
    method: str
    url: str
    headers: Optional[Dict[str, str]] = None
    body: Optional[Any] = None
    params: Optional[Dict[str, Any]] = None

@router.post("/run")
async def run_api_request(request_data: APIRequestSchema):
    """
    Tek bir API isteği çalıştırır ve sonucunu döner.
    """
    executor = APIExecutor()
    try:
        result = await executor.execute_step(
            method=request_data.method,
            path=request_data.url,
            json=request_data.body,
            headers=request_data.headers,
            params=request_data.params
        )
        return result
    finally:
        await executor.close()

@router.post("/batch")
async def run_batch_api_requests(requests: List[APIRequestSchema]):
    """
    Birden fazla API isteğini ardışık olarak çalıştırır.
    """
    executor = APIExecutor()
    try:
        results = []
        for req in requests:
            res = await executor.execute_step(
                method=req.method,
                path=req.url,
                json=req.body,
                headers=req.headers,
                params=req.params
            )
            results.append(res)
        return {
            "summary": executor.get_summary(),
            "results": results
        }
    finally:
        await executor.close()
@router.post("/load-test")
async def run_api_load_test(request_data: APIRequestSchema, count: int = 10):
    """Belirtilen API'ye yük testi yapar."""
    executor = APIExecutor()
    try:
        result = await executor.load_test(
            method=request_data.method,
            path=request_data.url,
            count=count,
            json=request_data.body,
            headers=request_data.headers
        )
        return result
    finally:
        await executor.close()

@router.get("/import-swagger")
async def import_swagger(url: str):
    """Swagger dökümanından uç noktaları getirir."""
    executor = APIExecutor()
    try:
        endpoints = await executor.parse_swagger(url)
        return endpoints
    finally:
        await executor.close()
