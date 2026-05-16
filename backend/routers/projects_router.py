
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

import schemas
from database import get_db
from database.models import Project, Page, TestCase, TestStep, PlatformType
from core.agents.case_generator import AICaseGenerator

router = APIRouter(prefix="/projects", tags=["projects"])

# ============================================
# PROJECT CRUD
# ============================================

@router.post("/", response_model=schemas.Project)
@router.post("", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    """Yeni proje oluştur (Örn: TRENDYOL)"""
    payload = project.model_dump() if hasattr(project, "model_dump") else project.dict()
    db_project = Project(**payload)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[schemas.Project])
@router.get("", response_model=List[schemas.Project])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Projeleri listele"""
    projects = (
        db.query(Project)
        .order_by(Project.created_at.desc(), Project.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return projects

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Projeyi ve bağlı tüm sayfaları/testleri sil"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return None

# ============================================
# PAGE (URL) MANAGEMENT (NEW)
# ============================================

@router.post("/{project_id}/pages", response_model=schemas.Page)
def add_page_to_project(project_id: int, page: schemas.PageBase, db: Session = Depends(get_db)):
    """Projeye yeni bir sayfa (URL) ekle (Örn: trendyol/login)"""
    db_page = Page(project_id=project_id, **page.dict())
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    return db_page

@router.get("/{project_id}/pages", response_model=List[schemas.Page])
def get_project_pages(project_id: int, db: Session = Depends(get_db)):
    """Projenin tüm sayfalarını (URL'lerini) listele"""
    return db.query(Page).filter(Page.project_id == project_id).all()

@router.delete("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(page_id: int, db: Session = Depends(get_db)):
    """Sayfayı ve bağlı tüm testleri sil"""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    db.delete(page)
    db.commit()
    return None

# ============================================
# AI CASE GENERATION (MODULAR)
# ============================================

@router.post("/pages/{page_id}/generate-cases")
async def generate_cases_for_page(
    page_id: int, 
    db: Session = Depends(get_db)
):
    """
    Belirli bir SAYFA (URL) için AI kullanarak otomatik test case üretir.
    """
    # 1. Sayfayı Bul
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    target_url = page.url
    
    try:
        # 2. AI ile Üret
        print(f"🤖 AI Case Generation başladı (Sayfa: {page.name}): {target_url}")
        generator = AICaseGenerator()
        generated_cases = await generator.generate_cases_from_url(
            target_url,
            platform="web",
            use_screenshot=True,
            strict_visual=False,
            require_live_show=False
        )
        if not generated_cases:
            raise HTTPException(
                status_code=500,
                detail="AI senaryo üretemedi. Görsel analiz veya canlı şov katmanı kontrol edilmeli."
            )

        # 3. Veritabanına Kaydet (Page ID ile)
        saved_cases = []
        try:
            for case_data in generated_cases:
                new_case = TestCase(
                    project_id=page.project_id,
                    page_id=page.id,
                    title=case_data.get("title", "Untitled Case"),
                    description=case_data.get("description", ""),
                    category=case_data.get("category", "happy_path"),
                    priority=case_data.get("priority", "medium"),
                    platform="web", # Şimdilik üretilenler web odaklı
                    status="draft"
                )
                db.add(new_case)
                db.commit()
                db.refresh(new_case)
                
                # Adımları Kaydet
                steps = case_data.get("steps", [])
                for step_data in steps:
                    new_step = TestStep(
                        test_case_id=new_case.id,
                        order=step_data.get("order", 1),
                        action=step_data.get("action", "verify"),
                        target=step_data.get("target", ""),
                        value=step_data.get("value", ""),
                        expected_result=step_data.get("expected_result", step_data.get("expected", ""))
                    )
                    db.add(new_step)
                
                db.commit()
                saved_cases.append(new_case)
                
            return {
                "message": f"{len(saved_cases)} cases generated for {page.name}.", 
                "cases": [{"id": c.id, "title": c.title, "category": c.category, "priority": c.priority} for c in saved_cases],
                "visual_analysis": generator.last_analysis_metadata,
            }

        except Exception as e:
            db.rollback()
            import traceback
            err = traceback.format_exc()
            print("DB ERROR:", err)
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=500, content={"detail": f"Database error: {str(e)}", "trace": err})
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print("GENERATE ERROR:", err)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": f"Generation error: {str(e)}", "trace": err})

# ============================================
# MANUAL CASE CRUD
# ============================================


def _serialize_case(test_case: TestCase) -> Dict[str, Any]:
    steps = sorted(test_case.steps, key=lambda step: step.order)
    return {
        "id": test_case.id,
        "project_id": test_case.project_id,
        "page_id": test_case.page_id,
        "title": test_case.title,
        "description": test_case.description,
        "category": test_case.category,
        "status": test_case.status,
        "priority": test_case.priority,
        "platform": test_case.platform,
        "steps": [
            {
                "id": step.id,
                "order": step.order,
                "action": step.action,
                "target": step.target,
                "value": step.value,
                "expected": step.expected_result,
                "expected_result": step.expected_result,
            }
            for step in steps
        ],
        "created_at": test_case.created_at,
    }


@router.post("/{project_id}/cases")
def create_manual_case(project_id: int, case_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Manuel test case oluşturur ve varsa adımlarını kaydeder."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    page_id = case_data.get("page_id")
    if page_id:
        page = db.query(Page).filter(Page.id == page_id, Page.project_id == project_id).first()
        if not page:
            raise HTTPException(status_code=404, detail="Page not found for this project")

    title = str(case_data.get("title", "")).strip()
    if not title:
        raise HTTPException(status_code=400, detail="Test case title is required")

    db_case = TestCase(
        project_id=project_id,
        page_id=page_id,
        title=title,
        description=case_data.get("description", ""),
        category=case_data.get("category", "happy_path"),
        status=case_data.get("status", "draft"),
        priority=case_data.get("priority", "medium"),
        platform=case_data.get("platform", "web"),
    )
    db.add(db_case)
    db.flush()

    for index, step_data in enumerate(case_data.get("steps", []) or [], start=1):
        db.add(TestStep(
            test_case_id=db_case.id,
            order=step_data.get("order", index),
            action=step_data.get("action", "verify"),
            target=step_data.get("target", ""),
            value=step_data.get("value"),
            expected_result=step_data.get("expected_result", step_data.get("expected", "")),
        ))

    db.commit()
    db.refresh(db_case)
    return _serialize_case(db_case)


@router.put("/cases/{case_id}")
def update_manual_case(case_id: int, case_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Manuel test case'i ve gönderildiyse adımlarını günceller."""
    db_case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    if "page_id" in case_data and case_data["page_id"]:
        page = db.query(Page).filter(
            Page.id == case_data["page_id"],
            Page.project_id == db_case.project_id,
        ).first()
        if not page:
            raise HTTPException(status_code=404, detail="Page not found for this project")

    for field in ["title", "description", "category", "status", "priority", "platform", "page_id"]:
        if field in case_data:
            setattr(db_case, field, case_data[field])

    if not str(db_case.title or "").strip():
        raise HTTPException(status_code=400, detail="Test case title is required")

    if "steps" in case_data:
        db.query(TestStep).filter(TestStep.test_case_id == case_id).delete()
        for index, step_data in enumerate(case_data.get("steps") or [], start=1):
            db.add(TestStep(
                test_case_id=case_id,
                order=step_data.get("order", index),
                action=step_data.get("action", "verify"),
                target=step_data.get("target", ""),
                value=step_data.get("value"),
                expected_result=step_data.get("expected_result", step_data.get("expected", "")),
            ))

    db.commit()
    db.refresh(db_case)
    return _serialize_case(db_case)


@router.delete("/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manual_case(case_id: int, db: Session = Depends(get_db)):
    """Manuel veya AI kaynaklı test case'i siler."""
    db_case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not db_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    db.delete(db_case)
    db.commit()
    return None
