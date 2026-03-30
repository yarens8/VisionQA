"""
VisionQA Backend - Pydantic Schemas
Data validation and serialization
"""

from typing import List, Optional, Any, Dict
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
    ai_critic: str
    why_this_matters: str
    bounding_box: BoundingBox
    crop_image_base64: str
    recommendation: str


class UiuxScoreSummary(BaseModel):
    ux_score: int
    visual_hierarchy_score: int
    spacing_score: int
    consistency_score: int
    readability_score: int
    friction_score: int
    focus_score: int


class UiuxAttentionPrediction(BaseModel):
    focus_score: int
    primary_focus_label: str
    attention_path: List[str]
    summary: str


class UiuxArtifacts(BaseModel):
    annotated_image_base64: str
    attention_overlay_image_base64: str
    source_image_base64: str


class UiuxAnalysisRequest(BaseModel):
    platform: str = "web"
    image_base64: str


class UiuxAnalysisResponse(BaseModel):
    platform: str
    image: AccessibilityImageMeta
    overall_score: int
    ux_score: int
    overview: str
    alignment_score: int
    spacing_consistency_score: int
    layout_balance_score: int
    visual_hierarchy_score: int
    readability_score: int
    consistency_score: int
    friction_score: int
    focus_score: int
    ai_critic_summary: str
    score_summary: UiuxScoreSummary
    attention_prediction: UiuxAttentionPrediction
    findings: List[UiuxFinding]
    artifacts: UiuxArtifacts
    recommendations: List[str]


class UiuxHistoryItem(BaseModel):
    id: int
    platform: str
    source_type: str
    source_label: Optional[str] = None
    is_favorite: bool = False
    overall_score: int
    findings_count: int
    overview: str
    thumbnail_base64: Optional[str] = None
    created_at: datetime


class UiuxHistoryDetail(BaseModel):
    id: int
    platform: str
    source_type: str
    source_label: Optional[str] = None
    is_favorite: bool = False
    created_at: datetime
    analysis: UiuxAnalysisResponse


class UiuxHistoryUpdateRequest(BaseModel):
    source_label: Optional[str] = None
    is_favorite: Optional[bool] = None


class UiuxHistoryDeleteResponse(BaseModel):
    success: bool


class SecurityFinding(BaseModel):
    id: int
    title: str
    severity: str
    layer: str
    category: str
    description: str
    bounding_box: BoundingBox
    crop_image_base64: str
    recommendation: str
    evidence: Optional[str] = None


class SecurityArtifacts(BaseModel):
    overlay_image_base64: str
    source_image_base64: str


class SecurityHeaderSummary(BaseModel):
    checked: int
    missing: int


class SecurityLayerSummary(BaseModel):
    score: int
    count: int
    overview: str


class SecurityAttackHypothesis(BaseModel):
    id: int
    title: str
    severity: str
    attack_type: str
    inferred_context: str
    target_surface: str
    rationale: str
    confidence: int
    priority: int
    payload_families: List[str]
    role_scenarios: List[str]
    evidence: List[str]
    recommended_test: str
    preconditions: List[str]
    playbook_steps: List[str]


class SecurityAttackChain(BaseModel):
    id: int
    title: str
    severity: str
    confidence: int
    summary: str
    linked_layers: List[str]
    linked_modules: List[str]
    linked_hypothesis_ids: List[int]
    linked_finding_ids: List[int]
    evidence: List[str]
    attack_path: List[str]
    remediation_path: List[str]


class SecurityRootCause(BaseModel):
    id: int
    title: str
    severity: str
    taxonomy: str
    confidence: int
    summary: str
    linked_categories: List[str]
    recommendations: List[str]
    remediation_bundles: dict[str, List[str]]


class SecurityContextProfile(BaseModel):
    primary_context: str
    detected_contexts: List[str]
    attack_readiness: int


class SecurityCrossModuleHint(BaseModel):
    module: str
    reason: str
    suggested_action: str
    priority: int


class SecuritySimulationRequest(BaseModel):
    url: str
    platform: str = "web"
    hypotheses: List[str] = []


class SecurityProbeResult(BaseModel):
    id: int
    probe_type: str
    status: str
    severity: str
    summary: str
    evidence: List[str]
    request_preview: str
    next_step: str


class SecuritySimulationResponse(BaseModel):
    url: str
    executed_count: int
    blocked_count: int
    overall_signal: str
    probes: List[SecurityProbeResult]
    recommendations: List[str]


class SecurityAnalysisRequest(BaseModel):
    platform: str = "web"
    image_base64: str


class SecurityUrlAnalysisRequest(BaseModel):
    url: str
    platform: str = "web"
    headless: bool = True
    full_page: bool = True


class SecurityAnalysisResponse(BaseModel):
    platform: str
    image: AccessibilityImageMeta
    overall_score: int
    overview: str
    visual_score: int
    surface_score: int
    hypothesis_score: int
    correlation_score: int
    findings: List[SecurityFinding]
    visual_findings: List[SecurityFinding]
    surface_findings: List[SecurityFinding]
    attack_hypotheses: List[SecurityAttackHypothesis]
    attack_chains: List[SecurityAttackChain]
    root_causes: List[SecurityRootCause]
    artifacts: SecurityArtifacts
    header_summary: SecurityHeaderSummary
    layer_summary: dict[str, SecurityLayerSummary]
    context_profile: SecurityContextProfile
    cross_module_hints: List[SecurityCrossModuleHint]
    recommendations: List[str]


class SecurityHistoryItem(BaseModel):
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


class SecurityHistoryDetail(BaseModel):
    id: int
    platform: str
    source_type: str
    source_label: Optional[str] = None
    source_url: Optional[str] = None
    is_favorite: bool = False
    created_at: datetime
    analysis: SecurityAnalysisResponse


class SecurityHistoryUpdateRequest(BaseModel):
    source_label: Optional[str] = None
    is_favorite: Optional[bool] = None


class SecurityHistoryDeleteResponse(BaseModel):
    success: bool


class ApiTestAnalyzeRequest(BaseModel):
    method: str
    url: str
    headers: Optional[Dict[str, str]] = None
    body: Optional[Any] = None
    params: Optional[Dict[str, Any]] = None
    expected_status: Optional[int] = None
    expected_fields: List[str] = []
    expected_response_type: Optional[str] = None
    run_negative_checks: bool = True


class ApiTestFinding(BaseModel):
    id: int
    title: str
    severity: str
    category: str
    description: str
    evidence: str
    recommendation: str


class ApiNegativeCheck(BaseModel):
    id: int
    name: str
    status: str
    summary: str
    evidence: str


class ApiGeneratedTest(BaseModel):
    id: int
    title: str
    category: str
    priority: int
    rationale: str
    suggested_payload: Optional[str] = None
    expected_signal: str


class ApiScoreBreakdown(BaseModel):
    health: int
    validation: int
    security: int
    performance: int
    contract: int


class ApiCrossModuleCorrelation(BaseModel):
    module: str
    summary: str
    reason: str
    suggested_follow_up: str


class ApiTestAnalyzeResponse(BaseModel):
    method: str
    url: str
    success: bool
    status_code: Optional[int] = None
    duration_ms: float
    overall_score: int
    endpoint_risk_score: int
    summary: str
    ai_failure_explanation: str
    ai_test_summary: str
    root_cause_summary: str
    endpoint_context: str
    response_type: str
    response_size: int
    score_breakdown: ApiScoreBreakdown
    findings: List[ApiTestFinding]
    negative_checks: List[ApiNegativeCheck]
    generated_tests: List[ApiGeneratedTest]
    cross_module_correlation: List[ApiCrossModuleCorrelation]
    raw_result: Dict[str, Any]


class DbQualityRequest(BaseModel):
    connection_string: str
    query: Optional[str] = None
    table_name: Optional[str] = None
    expected_columns: List[str] = []
    api_expected_fields: List[str] = []
    sample_limit: int = 50


class DbQualityFinding(BaseModel):
    id: int
    title: str
    severity: str
    category: str
    description: str
    evidence: str
    recommendation: str


class DbScoreBreakdown(BaseModel):
    integrity: int
    completeness: int
    consistency: int
    performance: int
    security: int


class DbConstraintSummary(BaseModel):
    primary_keys: List[str]
    foreign_keys: List[str]
    unique_columns: List[str]
    nullable_columns: List[str]


class DbSchemaSmell(BaseModel):
    id: int
    title: str
    summary: str
    severity: str


class DbQualityResponse(BaseModel):
    success: bool
    overall_score: int
    table_quality_score: int
    summary: str
    ai_interpretation: str
    root_cause_summary: str
    table_name: Optional[str] = None
    duration_ms: float
    score_breakdown: DbScoreBreakdown
    findings: List[DbQualityFinding]
    schema_smells: List[DbSchemaSmell]
    constraint_summary: Optional[DbConstraintSummary] = None
    query_result: Optional[Dict[str, Any]] = None
    schema_validation: Optional[Dict[str, Any]] = None
    detected_columns: List[str] = []
    sample_rows: List[Dict[str, Any]] = []
