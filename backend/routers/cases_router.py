
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

from database import get_db
from database.models import TestCase, TestStep, Project

router = APIRouter(prefix="/cases", tags=["Test Cases - AI Generation"])


# ─────────────────────────────────────────────
# Request / Response Modelleri
# ─────────────────────────────────────────────

class GenerateCasesRequest(BaseModel):
    url: str
    platform: str = "web"
    project_id: Optional[int] = None
    use_screenshot: bool = False  # True → Playwright ile gerçek analiz (yavaş ama doğru)

class TestStepResponse(BaseModel):
    order: int
    action: str
    target: str
    expected: str

class TestCaseResponse(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    category: str
    priority: str
    source_url: str
    steps: List[Dict[str, Any]]

class GenerateCasesResponse(BaseModel):
    success: bool
    url: str
    total_cases: int
    summary: Dict[str, int]
    cases: List[TestCaseResponse]
    saved_to_db: bool


# ─────────────────────────────────────────────
# Endpoint: AI ile Test Case Üret
# ─────────────────────────────────────────────

@router.post("/generate", response_model=GenerateCasesResponse)
async def generate_test_cases(
    request: GenerateCasesRequest,
    db: Session = Depends(get_db)
):
    """
    🤖 AI (Groq + Llama 3.3 70B + SAM3) ile test senaryoları üretir.

    - **url**: Test edilecek sayfa URL'si (örn: https://saucedemo.com)
    - **platform**: web | mobile | api
    - **project_id**: Üretilen case'leri hangi projeye kaydedeceği (opsiyonel)
    - **use_screenshot**: True = Gerçek browser screenshot analizi (yavaş), False = URL'den hızlı tahmin
    """
    try:
        from core.agents.case_generator import AICaseGenerator
        generator = AICaseGenerator()

        # AI ile senaryolar üret
        cases_data = await generator.generate_cases_from_url(
            url=request.url,
            platform=request.platform,
            use_screenshot=request.use_screenshot
        )

        if not cases_data:
            raise HTTPException(status_code=500, detail="AI senaryo üretemedi.")

        # Özet istatistikleri hesapla
        from collections import Counter
        category_counts = Counter(c["category"] for c in cases_data)

        # Eğer project_id verildiyse DB'ye kaydet
        saved_to_db = False
        saved_cases_map: Dict[str, int] = {}  # title -> db_id

        if request.project_id:
            # Projeyi doğrula
            project = db.query(Project).filter(Project.id == request.project_id).first()
            if not project:
                raise HTTPException(status_code=404, detail=f"Proje bulunamadı: {request.project_id}")

            # Her case'i DB'ye kaydet
            for case_data in cases_data:
                db_case = TestCase(
                    project_id=request.project_id,
                    title=case_data["title"],
                    description=case_data.get("description", ""),
                    status="draft",
                    priority=case_data.get("priority", "medium")
                )
                db.add(db_case)
                db.flush()  # ID almak için

                # Gerçek DB ID'sini kaydet
                saved_cases_map[case_data["title"]] = db_case.id

                # Adımları kaydet
                for step_data in case_data.get("steps", []):
                    db_step = TestStep(
                        test_case_id=db_case.id,
                        order=step_data.get("order", 1),
                        action=step_data.get("action", "interact"),
                        target=step_data.get("target", ""),
                        expected_result=step_data.get("expected", ""),
                        value=step_data.get("value", None)
                    )
                    db.add(db_step)

            db.commit()
            saved_to_db = True

        return GenerateCasesResponse(
            success=True,
            url=request.url,
            total_cases=len(cases_data),
            summary={
                "happy_path": category_counts.get("happy_path", 0),
                "negative_path": category_counts.get("negative_path", 0),
                "edge_case": category_counts.get("edge_case", 0),
                "security": category_counts.get("security", 0),
            },
            cases=[
                TestCaseResponse(
                    id=saved_cases_map.get(c["title"]),  # Gerçek DB ID veya None
                    title=c["title"],
                    description=c.get("description", ""),
                    category=c["category"],
                    priority=c.get("priority", "medium"),
                    source_url=c.get("source_url", request.url),
                    steps=c.get("steps", [])
                ) for c in cases_data
            ],
            saved_to_db=saved_to_db
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen hata: {str(e)}")


# ─────────────────────────────────────────────
# Endpoint: Tüm Test Case'leri Listele
# ─────────────────────────────────────────────

@router.get("/", response_model=List[Dict[str, Any]])
def list_test_cases(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Test case'leri listele. project_id veya status ile filtrele.
    """
    query = db.query(TestCase)

    if project_id:
        query = query.filter(TestCase.project_id == project_id)
    if status:
        query = query.filter(TestCase.status == status)

    cases = query.order_by(TestCase.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for case in cases:
        steps = sorted(case.steps, key=lambda s: s.order)
        result.append({
            "id": case.id,
            "project_id": case.project_id,
            "title": case.title,
            "description": case.description,
            "status": case.status,
            "priority": case.priority,
            "steps_count": len(steps),
            "steps": [
                {
                    "order": s.order,
                    "action": s.action,
                    "target": s.target,
                    "expected": s.expected_result
                } for s in steps
            ],
            "created_at": case.created_at,
        })

    return result


# ─────────────────────────────────────────────
# Endpoint: Tek Test Case Detayı
# ─────────────────────────────────────────────

@router.get("/{case_id}", response_model=Dict[str, Any])
def get_test_case(case_id: int, db: Session = Depends(get_db)):
    """Tekil test case detaylarını döndürür."""
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Test case bulunamadı.")

    steps = sorted(case.steps, key=lambda s: s.order)
    return {
        "id": case.id,
        "project_id": case.project_id,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "priority": case.priority,
        "steps": [
            {
                "order": s.order,
                "action": s.action,
                "target": s.target,
                "expected": s.expected_result,
                "value": s.value
            } for s in steps
        ],
        "created_at": case.created_at,
    }


# ─────────────────────────────────────────────
# Endpoint: Test Case Durumunu Güncelle
# ─────────────────────────────────────────────

class UpdateStatusRequest(BaseModel):
    status: str  # "draft" | "approved" | "deprecated"

@router.patch("/{case_id}/status")
def update_case_status(
    case_id: int,
    request: UpdateStatusRequest,
    db: Session = Depends(get_db)
):
    """Test case'in durumunu güncelle (draft → approved)."""
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Test case bulunamadı.")

    valid_statuses = ["draft", "approved", "deprecated"]
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Geçersiz durum. Olası değerler: {valid_statuses}")

    case.status = request.status
    db.commit()

    return {"success": True, "id": case_id, "new_status": request.status}
