import httpx
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

class APIExecutor:
    """
    🚀 VisionQA — API Executor (REST, GraphQL support)
    Bu sınıf, API test senaryolarını adım adım çalıştırmak için tasarlanmıştır.
    """

    def __init__(self, base_url: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url
        self.headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "VisionQA-API-Engine/1.0"
        }
        # base_url None ise AsyncClient'a gönderilmemeli (bazı versiyonlarda hata verebilir)
        client_kwargs = {"headers": self.headers, "timeout": 30.0}
        if base_url:
            client_kwargs["base_url"] = base_url
            
        self.client = httpx.AsyncClient(**client_kwargs)
        self.history: List[Dict[str, Any]] = []


    async def close(self):
        await self.client.aclose()

    async def execute_step(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        Tek bir API adımını (request) çalıştırır.
        """
        start_time = time.time()
        method = method.upper()
        
        # URL hazırlığı (eğer path tam bir URL değilse base_url ile birleştirir)
        url = path if path.startswith("http") else path

        # Body hazırlığı (JSON desteği)
        body = kwargs.get("json") or kwargs.get("data")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except:
                pass

        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=body if method != "GET" else None,
                params=kwargs.get("params"),
                headers=kwargs.get("headers")
            )
            
            duration = (time.time() - start_time) * 1000
            
            result = {
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
                "duration_ms": round(duration, 2),
                "response_body": response.json() if "application/json" in response.headers.get("content-type", "") else response.text,
                "headers": dict(response.headers),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.utcnow().isoformat()
            }

        self.history.append({
            "request": {"method": method, "url": url, "body": body},
            "response": result
        })
        
        return result

    async def graphql_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        GraphQL sorgularını kolaylaştırmak için yardımcı metod.
        """
        return await self.execute_step(
            method="POST",
            path="", # Genellikle base_url/graphql olur, base_url'e göre değişir
            json={"query": query, "variables": variables or {}}
        )

    async def load_test(self, method: str, path: str, count: int = 10, **kwargs) -> Dict[str, Any]:
        """Aynı anda birden fazla istek atarak yük testi yapar."""
        import asyncio
        start_time = time.time()
        tasks = [self.execute_step(method, path, **kwargs) for _ in range(count)]
        results = await asyncio.gather(*tasks)
        
        durations = [r.get("duration_ms", 0) for r in results]
        success_count = len([r for r in results if r.get("success")])
        
        return {
            "total_requests": count,
            "success_count": success_count,
            "avg_duration_ms": round(sum(durations) / count, 2) if count > 0 else 0,
            "p95_duration_ms": sorted(durations)[int(count * 0.95)] if count > 0 else 0,
            "total_time_ms": round((time.time() - start_time) * 1000, 2)
        }

    async def parse_swagger(self, swagger_url: str) -> List[Dict[str, Any]]:
        """Swagger/OpenAPI dökümanından uç noktaları çıkarır."""
        try:
            res = await self.client.get(swagger_url)
            data = res.json()
            endpoints = []
            paths = data.get("paths", {})
            for path, methods in paths.items():
                for method, info in methods.items():
                    endpoints.append({
                        "method": method.upper(),
                        "path": path,
                        "summary": info.get("summary", ""),
                        "tags": info.get("tags", [])
                    })
            return endpoints
        except Exception as e:
            print(f"Swagger parse error: {e}")
            return []

    def get_summary(self) -> Dict[str, Any]:

        """Tüm koşumun özetini döner."""
        return {
            "total_steps": len(self.history),
            "successful_steps": len([h for h in self.history if h["response"].get("success")]),
            "total_duration_ms": sum(h["response"].get("duration_ms", 0) for h in self.history),
            "history": self.history
        }
