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


class PerformanceAnalyzeRequest(BaseModel):
    url: Optional[str] = None
    api_url: Optional[str] = None
    api_method: str = "GET"
    db_connection_string: Optional[str] = None
    db_query: Optional[str] = None
    sample_api_runs: int = 5
    platform: str = "web"


class PerformanceFinding(BaseModel):
    id: int
    title: str
    severity: str
    category: str
    description: str
    evidence: str
    recommendation: str


class PerformanceScoreBreakdown(BaseModel):
    web: int
    api: int
    db: int
    technical: int
    perceived: int


class PerformanceWebMetrics(BaseModel):
    page_load_ms: float = 0
    dom_content_loaded_ms: float = 0
    fcp_ms: float = 0
    lcp_ms: float = 0
    tti_ms: float = 0
    cls: float = 0
    transfer_kb: float = 0


class PerformanceApiMetrics(BaseModel):
    avg_ms: float = 0
    p50_ms: float = 0
    p95_ms: float = 0
    p99_ms: float = 0
    error_rate: float = 0
    timeout_count: int = 0
    sample_count: int = 0


class PerformanceDbMetrics(BaseModel):
    duration_ms: float = 0
    row_count: int = 0
    success: bool = False


class PerformanceCorrelation(BaseModel):
    source: str
    summary: str
    reason: str


class PerformanceAnalysisResponse(BaseModel):
    platform: str
    overall_score: int
    technical_score: int
    perceived_score: int
    performance_grade: str
    bottleneck_confidence: int
    overview: str
    timeline_summary: List[str]
    root_cause_summary: str
    optimization_suggestions: List[str]
    module_recommendations: Dict[str, List[str]]
    score_breakdown: PerformanceScoreBreakdown
    web_metrics: Optional[PerformanceWebMetrics] = None
    api_metrics: Optional[PerformanceApiMetrics] = None
    db_metrics: Optional[PerformanceDbMetrics] = None
    findings: List[PerformanceFinding]
    correlations: List[PerformanceCorrelation]


class DatasetAnnotationRecord(BaseModel):
    label: Optional[str] = None
    bbox: Optional[List[float]] = None


class DatasetRecord(BaseModel):
    id: Optional[str] = None
    split: Optional[str] = None
    label: Optional[str] = None
    text: Optional[str] = None
    image_name: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    annotations: List[DatasetAnnotationRecord] = []
    metadata: Dict[str, Any] = {}


class DatasetAnalyzeRequest(BaseModel):
    dataset_name: str = "Dataset v1"
    records: List[DatasetRecord]


class DatasetFinding(BaseModel):
    id: int
    title: str
    severity: str
    category: str
    description: str
    evidence: str
    recommendation: str


class DatasetScoreBreakdown(BaseModel):
    completeness: int
    balance: int
    consistency: int
    validity: int
    annotation_health: int


class DatasetClassDistributionItem(BaseModel):
    label: str
    count: int
    ratio: float


class DatasetDuplicateSignal(BaseModel):
    id: int
    reason: str
    record_ids: List[str]


class DatasetSuspiciousLabelSignal(BaseModel):
    id: int
    record_id: str
    current_label: str
    reason: str
    suggested_review: str


class DatasetTrainingRisk(BaseModel):
    severity: str
    summary: str
    impacted_areas: List[str]


class DatasetSplitHealthItem(BaseModel):
    split: str
    count: int
    ratio: float


class DatasetCoverageGap(BaseModel):
    id: int
    title: str
    summary: str
    impacted_labels: List[str]


class DatasetCollectionTarget(BaseModel):
    label: str
    priority: int
    reason: str


class DatasetAnalysisResponse(BaseModel):
    dataset_name: str
    total_records: int
    overall_score: int
    quality_grade: str
    overview: str
    ai_interpretation: str
    training_risk_summary: str
    score_breakdown: DatasetScoreBreakdown
    findings: List[DatasetFinding]
    class_distribution: List[DatasetClassDistributionItem]
    split_health: List[DatasetSplitHealthItem]
    coverage_gaps: List[DatasetCoverageGap]
    duplicate_signals: List[DatasetDuplicateSignal]
    suspicious_label_signals: List[DatasetSuspiciousLabelSignal]
    synthetic_data_suggestions: List[str]
    collection_targets: List[DatasetCollectionTarget]
    model_impact_summary: str
    training_risks: List[DatasetTrainingRisk]


class MobileElementMetadata(BaseModel):
    element_type: str
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    text_content: Optional[str] = None
    aria_label: Optional[str] = None
    name: Optional[str] = None
    keyboard_focusable: Optional[bool] = None
    focus_visible: Optional[bool] = None


class MobileAnalysisRequest(BaseModel):
    platform: str = "android"
    screen_name: Optional[str] = None
    image_base64: Optional[str] = None
    element_metadata: List[MobileElementMetadata] = []


class MobileFinding(BaseModel):
    id: int
    title: str
    severity: str
    category: str
    description: str
    evidence: str
    recommendation: str


class MobileCapabilityItem(BaseModel):
    title: str
    status: str
    description: str


class MobileContextProfile(BaseModel):
    screen_type: str
    detected_patterns: List[str]
    cross_platform_consistency_signal: str


class MobileScoreBreakdown(BaseModel):
    mobile_ux: int
    touch_target: int
    readability: int
    layout: int
    interaction_readiness: int


class MobileAnalysisResponse(BaseModel):
    platform: str
    overall_score: int
    overview: str
    ai_interpretation: str
    ai_mobile_critic: str
    root_cause_summary: str
    task_completion_friction: int
    thumb_zone_summary: str
    keyboard_overlap_signal: str
    safe_area_signal: str
    gesture_friction_summary: str
    context_playbook: List[str]
    cross_platform_parity_summary: str
    score_breakdown: MobileScoreBreakdown
    context_profile: MobileContextProfile
    findings: List[MobileFinding]
    supported_now: List[MobileCapabilityItem]
    next_phase: List[MobileCapabilityItem]
    recommendations: List[str]
