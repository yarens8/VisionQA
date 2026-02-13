"""
VisionQA Backend - Pydantic Schemas
Data validation and serialization
"""

from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
from database.models import PlatformType, TestStatus


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
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==========================================
# TEST RUN SCHEMAS
# ==========================================

class TestRunBase(BaseModel):
    project_id: int
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
