
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from core.scenario_executor import ScenarioExecutor

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

class StepSchema(BaseModel):
    platform: str
    action: str
    params: Dict[str, Any]
    variable_output: Optional[str] = None

class ScenarioSchema(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[StepSchema]

@router.post("/run")
async def run_scenario(scenario: ScenarioSchema):
    """
    Gönderilen senaryo adımlarını sırasıyla çalıştırır.
    """
    executor = ScenarioExecutor()
    # Pydantic modellerini dict'e çeviriyoruz
    steps_dict = [step.dict() for step in scenario.steps]
    result = await executor.run_scenario(steps_dict)
    return result
