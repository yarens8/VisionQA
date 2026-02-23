
import asyncio
import json
import re
import time
from typing import List, Dict, Any, Optional
from executors.api.api_executor import APIExecutor
from executors.database.db_executor import DatabaseExecutor
from executors.web.web_executor import WebExecutor

class ScenarioExecutor:
    """
    🎭 VisionQA — Scenario Orchestrator
    Farklı platformlar arasındaki test adımlarını birleştirir ve veri paylaşımını sağlar.
    """
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        self.context = context or {}
        self.results = []
        self.stop_on_failure = True
        self.web_executor: Optional[WebExecutor] = None

    async def _get_web_executor(self) -> WebExecutor:
        if not self.web_executor:
            self.web_executor = WebExecutor(headless=True)
            await self.web_executor.start()
        return self.web_executor

    async def close(self):
        if self.web_executor:
            await self.web_executor.stop()
            self.web_executor = None

    def _resolve_variables(self, text: Any) -> Any:
        """Metin içindeki {{variable}} yapılarını context verileriyle doldurur."""
        if not isinstance(text, str):
            if isinstance(text, dict):
                return {k: self._resolve_variables(v) for k, v in text.items()}
            if isinstance(text, list):
                return [self._resolve_variables(i) for i in text]
            return text
            
        # Context'ten değer çekmek için {{key}} veya {{key.subkey}}
        matches = re.findall(r'\{\{(.*?)\}\}', text)
        for var in matches:
            var_name = var.strip()
            # Basit iç içe JSON desteği: key.subkey
            if "." in var_name:
                parts = var_name.split(".")
                val = self.context
                for part in parts:
                    if isinstance(val, dict):
                        val = val.get(part, f"{{{{{var_name}}}}}")
                    else:
                        break
            else:
                val = self.context.get(var_name, f"{{{{{var_name}}}}}")
            
            text = text.replace(f"{{{{{var}}}}}", str(val))
        return text

    async def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        platform = step.get("platform")
        action = step.get("action")
        params = self._resolve_variables(step.get("params", {}))
        var_output = step.get("variable_output")

        print(f"🎬 Senaryo Adımı: {platform} -> {action}")
        
        step_result = {"platform": platform, "action": action, "success": False, "duration_ms": 0}
        start_time = time.time()

        try:
            if platform == "api":
                executor = APIExecutor()
                res = await executor.execute_step(
                    method=params.get("method", "GET"),
                    path=params.get("url"),
                    json=params.get("body"),
                    headers=params.get("headers")
                )
                await executor.close()
                step_result.update(res)
                
                if var_output and res.get("success"):
                    self.context[var_output] = res.get("response")

            elif platform == "db":
                conn_string = params.get("connection_string")
                executor = DatabaseExecutor(conn_string)
                res = executor.execute_query(params.get("query"), params.get("params"))
                step_result.update(res)
                
                if var_output and res.get("success") and res.get("data"):
                    self.context[var_output] = res.get("data")[0] if len(res.get("data")) > 0 else None

            elif platform == "web":
                web = await self._get_web_executor()
                if action == "navigate":
                    await web.navigate(params.get("url"))
                    step_result["success"] = True
                elif action == "click":
                    await web.click_element(params.get("selector"))
                    step_result["success"] = True
                elif action == "type":
                    await web.type_input(params.get("selector"), params.get("text"))
                    step_result["success"] = True
                elif action == "verify":
                    step_result["success"] = await web.verify_element(params.get("selector"))
            
        except Exception as e:
            step_result["error"] = str(e)
            step_result["success"] = False

        step_result["duration_ms"] = int((time.time() - start_time) * 1000)
        self.results.append(step_result)
        return step_result

    async def run_scenario(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.results = []
        try:
            for step in steps:
                res = await self.execute_step(step)
                if not res.get("success") and self.stop_on_failure:
                    break
        finally:
            await self.close()
        
        return {
            "success": all(r.get("success") for r in self.results),
            "total_steps": len(steps),
            "executed_steps": len(self.results),
            "results": self.results,
            "final_context": self.context
        }

