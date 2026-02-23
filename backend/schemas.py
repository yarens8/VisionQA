"""
VisionQA Backend - Pydantic Schemas
Data validation and serialization
"""

from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
from database.models import PlatformType, TestStatus


# ==========================================
# PAGE SCHEMAS (NEW)
# ==========================================

class PageBase(BaseModel):
    name: str
    url: str
    description: Optional[str] = None

class PageCreate(PageBase):
    project_id: int

class Page(PageBase):
    id: int
    project_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==========================================
# PROJECT SCHEMAS
# ==========================================

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    platforms: List[PlatformType] = []

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    pages: List[Page] = []  # Proje artık sayfalarını da listeler
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==========================================
# TEST CASE SCHEMAS
# ==========================================

class TestStepBase(BaseModel):
    order: int
    action: str
    target: Optional[str] = None
    value: Optional[str] = None
    expected_result: Optional[str] = None

class TestStep(TestStepBase):
    id: int
    class Config:
        from_attributes = True

class TestCaseBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "draft"
    priority: str = "medium"

class TestCaseCreate(TestCaseBase):
    project_id: int
    page_id: Optional[int] = None

class TestCase(TestCaseBase):
    id: int
    project_id: int
    page_id: Optional[int] = None
    steps: List[TestStep] = []
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==========================================
# TEST RUN SCHEMAS
# ==========================================

class TestRunBase(BaseModel):
    project_id: int
    page_id: Optional[int] = None
    platform: PlatformType
    module_name: str
    target: str
    config: Optional[dict] = None

class TestRunCreate(TestRunBase):
    pass

class TestRun(TestRunBase):
    id: int
    status: TestStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==========================================
# FINDING SCHEMAS
# ==========================================

class FindingBase(BaseModel):
    title: str
    description: str
    severity: str
    category: str
    screenshot_url: Optional[str] = None
    extra_data: Optional[dict] = None

class FindingCreate(FindingBase):
    test_run_id: int

class Finding(FindingBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
