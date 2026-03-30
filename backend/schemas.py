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


# ==========================================
# ACCESSIBILITY SCHEMAS
# ==========================================

class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class AccessibilityFinding(BaseModel):
    id: int
    title: str
    severity: str
    category: str
    description: str
    wcag_status: str
    contrast_ratio: float
    dominant_dark: str
    dominant_light: str
    bounding_box: BoundingBox
    crop_image_base64: str
    recommendation: str


class AccessibilityHeatmapRegion(BaseModel):
    x: int
    y: int
    width: int
    height: int
    severity: str
    contrast_ratio: float


class AccessibilityImageMeta(BaseModel):
    width: int
    height: int


class AccessibilityWcagSummary(BaseModel):
    aaa_pass: int
    aa_pass: int
    large_text_only: int
    fail: int


class AccessibilityPaletteItem(BaseModel):
    color: str
    coverage: float


class AccessibilityComponentSummary(BaseModel):
    id: int
    label: str
    severity: str
    average_contrast_ratio: float
    bounding_box: BoundingBox


class AccessibilityArtifacts(BaseModel):
    overlay_image_base64: str
    source_image_base64: str


class AccessibilityElementMetadata(BaseModel):
    element_type: str
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    alt_text: Optional[str] = None
    aria_label: Optional[str] = None
    text_content: Optional[str] = None
    placeholder: Optional[str] = None
    title: Optional[str] = None
    value: Optional[str] = None
    name: Optional[str] = None
    input_type: Optional[str] = None
    keyboard_focusable: Optional[bool] = None
    focus_visible: Optional[bool] = None
    tab_index: Optional[int] = None


class AccessibilityAnalysisRequest(BaseModel):
    platform: str = "web"
    image_base64: str
    element_metadata: List[AccessibilityElementMetadata] = []


class AccessibilityUrlAnalysisRequest(BaseModel):
    url: str
    platform: str = "web"
    headless: bool = True
    full_page: bool = True


class AccessibilityAnalysisResponse(BaseModel):
    platform: str
    image: AccessibilityImageMeta
    overall_score: int
    overview: str
    wcag_summary: AccessibilityWcagSummary
    color_consistency_score: int
    palette: List[AccessibilityPaletteItem]
    components: List[AccessibilityComponentSummary]
    findings: List[AccessibilityFinding]
    heatmap: List[AccessibilityHeatmapRegion]
    artifacts: AccessibilityArtifacts
    recommendations: List[str]


class AccessibilityHistoryItem(BaseModel):
    id: int
    platform: str
    source_type: str
    source_label: Optional[str] = None
    source_url: Optional[str] = None
    is_favorite: bool = False
    overall_score: int
    findings_count: int
    overview: str
    thumbnail_base64: Optional[str] = None
    created_at: datetime


class AccessibilityHistoryDetail(BaseModel):
    id: int
    platform: str
    source_type: str
    source_label: Optional[str] = None
    source_url: Optional[str] = None
    is_favorite: bool = False
    created_at: datetime
    analysis: AccessibilityAnalysisResponse


class AccessibilityHistoryUpdateRequest(BaseModel):
    source_label: Optional[str] = None
    is_favorite: Optional[bool] = None


class AccessibilityHistoryDeleteResponse(BaseModel):
    success: bool


class UiuxFinding(BaseModel):
    id: int
    title: str
    severity: str
    category: str
    affected_role: str
    description: str
    bounding_box: BoundingBox
    crop_image_base64: str
    recommendation: str


class UiuxArtifacts(BaseModel):
    annotated_image_base64: str
    source_image_base64: str


class UiuxAnalysisRequest(BaseModel):
    platform: str = "web"
    image_base64: str


class UiuxAnalysisResponse(BaseModel):
    platform: str
    image: AccessibilityImageMeta
    overall_score: int
    overview: str
    alignment_score: int
    spacing_consistency_score: int
    layout_balance_score: int
    findings: List[UiuxFinding]
    artifacts: UiuxArtifacts
    recommendations: List[str]
