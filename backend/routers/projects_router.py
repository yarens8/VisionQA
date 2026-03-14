
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
    db_project = Project(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[schemas.Project])
@router.get("", response_model=List[schemas.Project])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Projeleri listele"""
    projects = db.query(Project).offset(skip).limit(limit).all()
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
            strict_visual=True,
            require_live_show=True
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
                "cases": [{"id": c.id, "title": c.title, "category": c.category, "priority": c.priority} for c in saved_cases]
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

@router.post("/{project_id}/cases")
def create_manual_case(project_id: int, case_data: Dict[str, Any], db: Session = Depends(get_db)):
    # ... Manuel case oluşturma mantığı (Gerekirse page_id eklenebilir)
    pass
