import axios from 'axios';

// 🌐 Axios Instance (Base Config)
const apiClient = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

const backendBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Interceptor (Hata yakalama, Token ekleme vb. için)
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error("API Hatası:", error.response?.data || error.message);
        return Promise.reject(error);
    }
);

// 📦 Veri Tipleri (Backend Modelim)

export interface Page {
    id: number;
    project_id: number;
    name: string;
    url: string;
    description?: string;
    created_at: string;
}

export interface PageCreate {
    project_id: number;
    name: string;
    url: string;
    description?: string;
}

export interface Project {
    id: number;
    name: string;
    description?: string;
    platforms: string[];
    pages: Page[]; // Proje artık sayfalarını da taşır
    created_at: string;
    updated_at: string;
}

export interface ProjectCreate {
    name: string;
    description?: string;
    platforms: string[];
}

export interface TestStep {
    id?: number;
    order: number;
    action: string;
    target: string;
    value?: string;
    expected_result?: string;
    expected?: string;
}

export interface TestCase {
    id: number;
    project_id: number;
    page_id?: number;
    title: string;
    description?: string;
    status: 'draft' | 'approved' | 'archived';
    priority: string;
    category?: string;
    source_url?: string;
    steps: TestStep[];
    created_at: string;
}

export interface GenerateCasesRequest {
    url: string;
    platform?: string;
    project_id?: number;
    page_id?: number;
    use_screenshot?: boolean;
    strict_visual?: boolean;
    require_live_show?: boolean;
}

export interface GenerateCasesResponse {
    success: boolean;
    url: string;
    total_cases: number;
    saved_cases?: number;
    summary: { happy_path: number; negative_path: number; edge_case: number; security: number };
    cases: TestCase[];
    saved_to_db: boolean;
    visual_analysis?: {
        vision_provider?: string;
        detected_element_count?: number;
        visual_fallback_used?: boolean;
        fallback_reason?: string;
        detected_elements?: { label?: string; score?: number; box?: number[] }[];
        screenshot_base64?: string;
        annotated_screenshot_base64?: string;
        live_overlay_requested?: boolean;
        live_overlay_status?: 'not_requested' | 'starting' | 'shown' | 'unavailable' | string;
        live_overlay_error?: string;
    };
}

export interface RunStartResponse {
    run_id: number;
    case_id: number;
    status: 'running' | 'completed' | 'failed' | 'crashed';
    live_mode?: boolean;
}

export interface RunStatusResponse {
    run_id: number;
    case_id: number;
    status: 'running' | 'completed' | 'failed' | 'crashed';
    summary?: string;
    steps: any[];
    bug_analysis?: BugAnalysisReport[];
}

export interface StartCaseRequest {
    live_mode?: boolean;
}

export interface DashboardStats {
    total_projects: number;
    total_cases: number;
    recent_runs: number;
    success_rate: number;
    platform_breakdown: { platform: string; total_runs: number; success_rate: number }[];
    recent_test_runs: { id: number; case_title: string; platform: string; module: string; created_at: string; duration: string; status: string }[];
    weekly_trend: { date: string; count: number }[];
}

export interface Alert {
    title: string;
    message: string;
    severity: 'high' | 'medium' | 'low';
    action: string;
}

export interface AlertsResponse {
    total_alerts: number;
    critical_count: number;
    warning_count: number;
    alerts: Alert[];
}

export interface AccessibilityBoundingBox {
    x: number;
    y: number;
    width: number;
    height: number;
}

export interface AccessibilityFinding {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | 'pass' | string;
    category: string;
    description: string;
    wcag_status: string;
    contrast_ratio: number;
    dominant_dark: string;
    dominant_light: string;
    bounding_box: AccessibilityBoundingBox;
    crop_image_base64: string;
    recommendation: string;
}

export interface AccessibilityHeatmapRegion {
    x: number;
    y: number;
    width: number;
    height: number;
    severity: 'high' | 'medium' | 'low' | 'pass' | string;
    contrast_ratio: number;
}

export interface AccessibilityAnalysisResponse {
    platform: string;
    image: {
        width: number;
        height: number;
    };
    overall_score: number;
    overview: string;
    wcag_summary: {
        aaa_pass: number;
        aa_pass: number;
        large_text_only: number;
        fail: number;
    };
    color_consistency_score: number;
    palette: {
        color: string;
        coverage: number;
    }[];
    components: {
        id: number;
        label: string;
        severity: 'high' | 'medium' | 'low' | 'pass' | string;
        average_contrast_ratio: number;
        bounding_box: AccessibilityBoundingBox;
    }[];
    findings: AccessibilityFinding[];
    heatmap: AccessibilityHeatmapRegion[];
    artifacts: {
        overlay_image_base64: string;
        source_image_base64: string;
    };
    recommendations: string[];
}

export interface AccessibilityUrlAnalysisRequest {
    url: string;
    platform?: string;
    headless?: boolean;
    full_page?: boolean;
}

export interface AccessibilityHistoryItem {
    id: number;
    platform: string;
    source_type: string;
    source_label?: string;
    source_url?: string;
    is_favorite: boolean;
    overall_score: number;
    findings_count: number;
    overview: string;
    thumbnail_base64?: string;
    created_at: string;
}

export interface AccessibilityHistoryDetail {
    id: number;
    platform: string;
    source_type: string;
    source_label?: string;
    source_url?: string;
    is_favorite: boolean;
    created_at: string;
    analysis: AccessibilityAnalysisResponse;
}

export interface AccessibilityHistoryUpdateRequest {
    source_label?: string;
    is_favorite?: boolean;
}

export interface UiuxFinding {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | 'pass' | string;
    category: string;
    affected_role: string;
    description: string;
    ai_critic: string;
    why_this_matters: string;
    bounding_box: AccessibilityBoundingBox;
    crop_image_base64: string;
    recommendation: string;
}

export interface UiuxScoreSummary {
    ux_score: number;
    visual_hierarchy_score: number;
    spacing_score: number;
    consistency_score: number;
    readability_score: number;
    friction_score: number;
    focus_score: number;
}

export interface UiuxAttentionPrediction {
    focus_score: number;
    primary_focus_label: string;
    attention_path: string[];
    summary: string;
}

export interface UiuxAnalysisResponse {
    platform: string;
    image: {
        width: number;
        height: number;
    };
    overall_score: number;
    ux_score: number;
    overview: string;
    alignment_score: number;
    spacing_consistency_score: number;
    layout_balance_score: number;
    visual_hierarchy_score: number;
    readability_score: number;
    consistency_score: number;
    friction_score: number;
    focus_score: number;
    ai_critic_summary: string;
    score_summary: UiuxScoreSummary;
    attention_prediction: UiuxAttentionPrediction;
    findings: UiuxFinding[];
    artifacts: {
        annotated_image_base64: string;
        attention_overlay_image_base64: string;
        source_image_base64: string;
    };
    recommendations: string[];
}

export interface UiuxHistoryItem {
    id: number;
    platform: string;
    source_type: string;
    source_label?: string;
    is_favorite: boolean;
    overall_score: number;
    findings_count: number;
    overview: string;
    thumbnail_base64?: string;
    created_at: string;
}

export interface UiuxHistoryDetail {
    id: number;
    platform: string;
    source_type: string;
    source_label?: string;
    is_favorite: boolean;
    created_at: string;
    analysis: UiuxAnalysisResponse;
}

export interface UiuxHistoryUpdateRequest {
    source_label?: string;
    is_favorite?: boolean;
}

export interface SecurityFinding {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | string;
    layer: 'visual' | 'surface' | string;
    category: string;
    description: string;
    bounding_box: AccessibilityBoundingBox;
    crop_image_base64: string;
    recommendation: string;
    evidence?: string;
}

export interface SecurityLayerSummary {
    score: number;
    count: number;
    overview: string;
}

export interface SecurityAttackHypothesis {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | string;
    attack_type: string;
    inferred_context: string;
    target_surface: string;
    rationale: string;
    confidence: number;
    priority: number;
    payload_families: string[];
    role_scenarios: string[];
    evidence: string[];
    recommended_test: string;
    preconditions: string[];
    playbook_steps: string[];
}

export interface SecurityAttackChain {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | string;
    confidence: number;
    summary: string;
    linked_layers: string[];
    linked_modules: string[];
    linked_hypothesis_ids: number[];
    linked_finding_ids: number[];
    evidence: string[];
    attack_path: string[];
    remediation_path: string[];
}

export interface SecurityRootCause {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | string;
    taxonomy: string;
    confidence: number;
    summary: string;
    linked_categories: string[];
    recommendations: string[];
    remediation_bundles: Record<string, string[]>;
}

export interface SecurityContextProfile {
    primary_context: string;
    detected_contexts: string[];
    attack_readiness: number;
}

export interface SecurityScanEvidence {
    source: string;
    url?: string;
    final_url?: string;
    status_code?: number | null;
    content_type?: string | null;
    ocr_regions: number;
    ocr_text_chars: number;
    response_text_chars: number;
    headers_observed: number;
    security_headers_checked: number;
    security_headers_missing: number;
    cookie_header_present: boolean;
    checks_executed: string[];
    collection_errors: string[];
}

export interface SecurityPriorityAction {
    title: string;
    severity: 'critical' | 'high' | 'medium' | 'low' | string;
    category: string;
    source: string;
    evidence: string;
    recommendation: string;
}

export interface SecurityRiskSummary {
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
    highest_severity: string;
    priority_actions: SecurityPriorityAction[];
}

export interface SecurityCrossModuleHint {
    module: string;
    reason: string;
    suggested_action: string;
    priority: number;
}

export interface SecuritySimulationRequest {
    url: string;
    platform?: string;
    hypotheses?: string[];
}

export interface SecurityProbeResult {
    id: number;
    probe_type: string;
    status: string;
    severity: 'high' | 'medium' | 'low' | string;
    summary: string;
    evidence: string[];
    request_preview: string;
    next_step: string;
}

export interface SecuritySimulationResponse {
    url: string;
    executed_count: number;
    blocked_count: number;
    overall_signal: string;
    probes: SecurityProbeResult[];
    recommendations: string[];
}

export interface SecurityHistoryItem {
    id: number;
    platform: string;
    source_type: string;
    source_label?: string;
    source_url?: string;
    is_favorite: boolean;
    overall_score: number;
    findings_count: number;
    overview: string;
    thumbnail_base64?: string;
    created_at: string;
}

export interface SecurityHistoryDetail {
    id: number;
    platform: string;
    source_type: string;
    source_label?: string;
    source_url?: string;
    is_favorite: boolean;
    created_at: string;
    analysis: SecurityAnalysisResponse;
}

export interface SecurityHistoryUpdateRequest {
    source_label?: string;
    is_favorite?: boolean;
}

export interface SecurityAnalysisResponse {
    platform: string;
    image: {
        width: number;
        height: number;
    };
    overall_score: number;
    overview: string;
    visual_score: number;
    surface_score: number;
    hypothesis_score: number;
    correlation_score: number;
    findings: SecurityFinding[];
    visual_findings: SecurityFinding[];
    surface_findings: SecurityFinding[];
    attack_hypotheses: SecurityAttackHypothesis[];
    attack_chains: SecurityAttackChain[];
    root_causes: SecurityRootCause[];
    artifacts: {
        overlay_image_base64: string;
        source_image_base64: string;
    };
    header_summary: {
        checked: number;
        missing: number;
    };
    layer_summary: Record<string, SecurityLayerSummary>;
    context_profile: SecurityContextProfile;
    scan_evidence: SecurityScanEvidence;
    risk_summary: SecurityRiskSummary;
    cross_module_hints: SecurityCrossModuleHint[];
    recommendations: string[];
}

export interface SecurityUrlAnalysisRequest {
    url: string;
    platform?: string;
    headless?: boolean;
    full_page?: boolean;
}

export interface ProjectSummaryReport {
    project: {
        id: number;
        name: string;
        description?: string;
        platforms: string[];
        pages_count: number;
    };
    generated_at: string;
    overall_score: number;
    summary: {
        total_runs: number;
        passed_runs: number;
        failed_runs: number;
        security_records: number;
        high_security_risks: number;
        medium_security_risks: number;
        test_actions: number;
        correlations: number;
        bug_reports?: number;
        api_actions?: number;
    };
    security: {
        records: Array<{
            id: number;
            source_type: string;
            source_label?: string;
            source_url?: string;
            overall_score: number;
            findings_count: number;
            overview: string;
            created_at?: string;
            risk_summary?: SecurityRiskSummary;
            priority_actions: SecurityPriorityAction[];
            scan_evidence: {
                status_code?: number | null;
                final_url?: string;
                headers_observed: number;
                checks_executed: number;
            };
        }>;
        priority_actions: SecurityPriorityAction[];
    };
    tests: {
        priority_actions: Array<{
            title: string;
            severity: string;
            source: string;
            module: string;
            run_id: number;
            test_case_id?: number;
            page_id?: number;
            target: string;
            run_target?: string;
            summary: string;
            recommendation: string;
            bug_report?: BugAnalysisReport;
        }>;
        bug_reports?: BugAnalysisReport[];
    };
    api?: {
        records: Array<{
            id?: number;
            module?: string;
            source_type?: string;
            source_label?: string;
            source_url?: string;
            overall_score?: number;
            findings_count?: number;
            overview?: string;
            created_at?: string;
            method?: string;
            status_code?: number | null;
            duration_ms?: number | null;
            endpoint_context?: string;
            endpoint_risk_score?: number;
            score_breakdown?: Record<string, number>;
            evidence_summary?: ApiEvidenceSummary;
            finding_categories?: string[];
        }>;
        priority_actions: Array<{
            title: string;
            severity: string;
            category: string;
            source: string;
            api_record_id?: number;
            api_record_ids?: number[];
            duplicate_count?: number;
            endpoint?: string;
            method?: string;
            status_code?: number | null;
            duration_ms?: number | null;
            summary: string;
            evidence: string;
            recommendation: string;
            score_breakdown?: Record<string, number>;
            evidence_summary?: ApiEvidenceSummary;
        }>;
    };
    correlation: {
        items: Array<{
            title: string;
            severity: string;
            target: string;
            related_modules: string[];
            signal_count: number;
            duplicate_count?: number;
            security_record_id?: number;
            run_ids: number[];
            evidence: {
                security: string[];
                tests: string[];
                bug_categories?: string[];
            };
            recommendation: string;
        }>;
    };
    module_breakdown?: {
        items: Array<{
            module: string;
            label: string;
            status: string;
            score?: number | null;
            records: number;
            findings: number;
            summary: string;
            latest: Array<{
                id?: number;
                module?: string;
                source_type?: string;
                source_label?: string;
                source_url?: string;
                overall_score?: number;
                findings_count?: number;
                overview?: string;
                created_at?: string;
            } | BugAnalysisReport | any>;
        }>;
    };
    runs: Array<{
        id: number;
        module_name: string;
        target: string;
        status: string;
        page_id?: number;
        page_name?: string;
        test_case_id?: number;
        test_case_title?: string;
        findings_count: number;
        failed_steps_count: number;
        created_at?: string;
        completed_at?: string;
        bug_reports_count?: number;
    }>;
}

export interface BugAnalysisReport {
    title: string;
    category: string;
    severity: string;
    affected_case?: string;
    run_target?: string;
    failed_step_order?: number;
    failed_action?: string;
    target: string;
    selector_used?: string;
    probable_cause: string;
    recommendation: string;
    evidence: {
        reason: string;
        duration_ms?: number;
        screenshot?: string;
        screenshot_error?: string;
        attempts?: Array<{ selector: string; error: string }>;
    };
}

export interface ApiTestAnalyzeRequest {
    method: string;
    url: string;
    project_id?: number;
    headers?: Record<string, string>;
    body?: any;
    params?: Record<string, any>;
    expected_status?: number;
    expected_fields?: string[];
    expected_response_type?: string;
    run_negative_checks?: boolean;
}

export interface ApiTestFinding {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | string;
    category: string;
    description: string;
    evidence: string;
    recommendation: string;
}

export interface ApiNegativeCheck {
    id: number;
    name: string;
    status: string;
    summary: string;
    evidence: string;
}

export interface ApiGeneratedTest {
    id: number;
    title: string;
    category: string;
    priority: number;
    rationale: string;
    suggested_payload?: string | null;
    expected_signal: string;
}

export interface ApiScoreBreakdown {
    health: number;
    validation: number;
    security: number;
    performance: number;
    contract: number;
}

export interface ApiEvidenceSummary {
    contract_signals: number;
    security_signals: number;
    performance_signals: number;
    validation_signals: number;
    availability_signals: number;
    negative_probe_signals: number;
    primary_categories: string[];
    recommended_modules: string[];
}

export interface ApiCrossModuleCorrelation {
    module: string;
    summary: string;
    reason: string;
    suggested_follow_up: string;
}

export interface ApiTestAnalyzeResponse {
    method: string;
    url: string;
    project_id?: number | null;
    success: boolean;
    status_code?: number;
    duration_ms: number;
    overall_score: number;
    endpoint_risk_score: number;
    summary: string;
    ai_failure_explanation: string;
    ai_test_summary: string;
    root_cause_summary: string;
    endpoint_context: string;
    response_type: string;
    response_size: number;
    score_breakdown: ApiScoreBreakdown;
    evidence_summary: ApiEvidenceSummary;
    findings: ApiTestFinding[];
    negative_checks: ApiNegativeCheck[];
    generated_tests: ApiGeneratedTest[];
    cross_module_correlation: ApiCrossModuleCorrelation[];
    raw_result: Record<string, any>;
}

export interface ApiHistoryItem {
    id: number;
    platform: string;
    source_type: string;
    source_label?: string | null;
    source_url?: string | null;
    project_id?: number | null;
    method?: string | null;
    success?: boolean | null;
    status_code?: number | null;
    duration_ms?: number | null;
    overall_score: number;
    findings_count: number;
    overview?: string | null;
    endpoint_context?: string | null;
    created_at?: string | null;
}

export interface ApiHistoryDetail extends ApiHistoryItem {
    analysis_payload?: ApiTestAnalyzeResponse;
}

export interface DbQualityRequest {
    connection_string: string;
    query?: string;
    table_name?: string;
    expected_columns?: string[];
    api_expected_fields?: string[];
    sample_limit?: number;
}

export interface DbQualityFinding {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | string;
    category: string;
    description: string;
    evidence: string;
    recommendation: string;
}

export interface DbScoreBreakdown {
    integrity: number;
    completeness: number;
    consistency: number;
    performance: number;
    security: number;
}

export interface DbConstraintSummary {
    primary_keys: string[];
    foreign_keys: string[];
    unique_columns: string[];
    nullable_columns: string[];
}

export interface DbSchemaSmell {
    id: number;
    title: string;
    summary: string;
    severity: 'high' | 'medium' | 'low' | string;
}

export interface DbQualityResponse {
    success: boolean;
    overall_score: number;
    table_quality_score: number;
    summary: string;
    ai_interpretation: string;
    root_cause_summary: string;
    table_name?: string;
    duration_ms: number;
    score_breakdown: DbScoreBreakdown;
    findings: DbQualityFinding[];
    schema_smells: DbSchemaSmell[];
    constraint_summary?: DbConstraintSummary | null;
    query_result?: Record<string, any> | null;
    schema_validation?: Record<string, any> | null;
    detected_columns: string[];
    sample_rows: Record<string, any>[];
}

export interface DbHistoryItem {
    id: number;
    platform: string;
    source_type: string;
    source_label?: string | null;
    source_url?: string | null;
    overall_score: number;
    findings_count: number;
    overview?: string | null;
    success?: boolean | null;
    table_name?: string | null;
    table_quality_score?: number | null;
    duration_ms?: number | null;
    detected_columns_count: number;
    created_at?: string | null;
}

export interface DbHistoryDetail extends DbHistoryItem {
    analysis_payload?: DbQualityResponse;
}

export interface PerformanceAnalyzeRequest {
    url?: string;
    api_url?: string;
    project_id?: number;
    api_method?: string;
    db_connection_string?: string;
    db_query?: string;
    sample_api_runs?: number;
    platform?: string;
}

export interface PerformanceFinding {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | string;
    category: string;
    description: string;
    evidence: string;
    recommendation: string;
}

export interface PerformanceScoreBreakdown {
    web: number;
    api: number;
    db: number;
    technical: number;
    perceived: number;
}

export interface PerformanceWebMetrics {
    page_load_ms: number;
    dom_content_loaded_ms: number;
    fcp_ms: number;
    lcp_ms: number;
    tti_ms: number;
    cls: number;
    transfer_kb: number;
}

export interface PerformanceApiMetrics {
    avg_ms: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
    error_rate: number;
    timeout_count: number;
    sample_count: number;
}

export interface PerformanceDbMetrics {
    duration_ms: number;
    row_count: number;
    success: boolean;
}

export interface PerformanceCorrelation {
    source: string;
    summary: string;
    reason: string;
}

export interface PerformanceAnalysisResponse {
    platform: string;
    overall_score: number;
    technical_score: number;
    perceived_score: number;
    performance_grade: string;
    bottleneck_confidence: number;
    overview: string;
    timeline_summary: string[];
    root_cause_summary: string;
    optimization_suggestions: string[];
    module_recommendations: Record<string, string[]>;
    score_breakdown: PerformanceScoreBreakdown;
    web_metrics?: PerformanceWebMetrics | null;
    api_metrics?: PerformanceApiMetrics | null;
    db_metrics?: PerformanceDbMetrics | null;
    findings: PerformanceFinding[];
    correlations: PerformanceCorrelation[];
}

export interface PerformanceHistoryItem {
    id: number;
    platform: string;
    source_type: string;
    source_label?: string | null;
    source_url?: string | null;
    project_id?: number | null;
    overall_score: number;
    findings_count: number;
    overview?: string | null;
    performance_grade?: string | null;
    technical_score?: number | null;
    perceived_score?: number | null;
    bottleneck_confidence?: number | null;
    created_at?: string | null;
}

export interface PerformanceHistoryDetail extends PerformanceHistoryItem {
    analysis_payload?: PerformanceAnalysisResponse;
}

export interface DatasetAnnotationRecord {
    id?: string;
    label?: string;
    bbox?: number[];
    category_id?: any;
}

export interface DatasetRecord {
    id?: string;
    split?: string;
    label?: string;
    text?: string;
    image_name?: string;
    width?: number;
    height?: number;
    annotations?: DatasetAnnotationRecord[];
    metadata?: Record<string, any>;
}

export interface DatasetAnalyzeRequest {
    dataset_name?: string;
    records: DatasetRecord[];
}

export type DatasetAnalyzePayload = DatasetAnalyzeRequest | DatasetRecord[] | Record<string, any>;

export interface DatasetFinding {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | string;
    category: string;
    description: string;
    evidence: string;
    recommendation: string;
    error_type?: string;
    image_id?: string;
    annotation_id?: string;
    file_name?: string;
    field?: string;
}

export interface DatasetDetailError {
    error_id: string;
    error_type: string;
    image_id?: string | null;
    annotation_id?: string | null;
    file_name?: string | null;
    field: string;
    severity: 'high' | 'medium' | 'low' | string;
    message: string;
    source: string;
    metadata: Record<string, any>;
}

export interface DatasetScoreBreakdown {
    completeness: number;
    balance: number;
    consistency: number;
    validity: number;
    annotation_health: number;
}

export interface DatasetClassDistributionItem {
    label: string;
    count: number;
    ratio: number;
}

export interface DatasetDuplicateSignal {
    id: number;
    reason: string;
    record_ids: string[];
}

export interface DatasetSuspiciousLabelSignal {
    id: number;
    record_id: string;
    current_label: string;
    reason: string;
    suggested_review: string;
}

export interface DatasetTrainingRisk {
    severity: 'high' | 'medium' | 'low' | string;
    summary: string;
    impacted_areas: string[];
}

export interface DatasetSplitHealthItem {
    split: string;
    count: number;
    ratio: number;
}

export interface DatasetCoverageGap {
    id: number;
    title: string;
    summary: string;
    impacted_labels: string[];
}

export interface DatasetCollectionTarget {
    label: string;
    priority: number;
    reason: string;
}

export interface DatasetAnalysisResponse {
    dataset_name: string;
    total_records: number;
    overall_score: number;
    quality_grade: string;
    overview: string;
    ai_interpretation: string;
    training_risk_summary: string;
    score_breakdown: DatasetScoreBreakdown;
    findings: DatasetFinding[];
    detail_errors: DatasetDetailError[];
    class_distribution: DatasetClassDistributionItem[];
    split_health: DatasetSplitHealthItem[];
    coverage_gaps: DatasetCoverageGap[];
    duplicate_signals: DatasetDuplicateSignal[];
    suspicious_label_signals: DatasetSuspiciousLabelSignal[];
    synthetic_data_suggestions: string[];
    collection_targets: DatasetCollectionTarget[];
    model_impact_summary: string;
    training_risks: DatasetTrainingRisk[];
    source_artifact?: {
        type: string;
        label?: string;
        path: string;
        sha256: string;
        size_bytes: number;
        saved_at: string;
    } | null;
}

export interface DatasetTicketWorkItem {
    source: string;
    severity: 'high' | 'medium' | 'low' | string;
    category: string;
    title: string;
    description: string;
    evidence: string;
    recommendation: string;
}

export interface DatasetTicket {
    provider: 'jira' | string;
    ticket_key: string;
    title: string;
    description: string;
    priority: 'high' | 'medium' | 'low' | string;
    status: string;
    module: string;
    dataset_name: string;
    quality_grade: string;
    overall_score: number;
    total_records: number;
    summary: {
        findings_count: number;
        detail_errors_count: number;
        high_count: number;
        medium_count: number;
    };
    work_items: DatasetTicketWorkItem[];
}

export interface DatasetTicketResponse {
    success: boolean;
    provider: 'jira' | string;
    configured: boolean;
    ticket: DatasetTicket;
    message: string;
}

export interface DatasetHistoryItem {
    id: number;
    dataset_name: string;
    source_type: string;
    source_label?: string;
    overall_score: number;
    quality_grade: string;
    findings_count: number;
    detail_errors_count: number;
    total_records: number;
    created_at: string;
}

export interface DatasetHistoryDetail {
    id: number;
    dataset_name: string;
    source_type: string;
    source_label?: string;
    created_at: string;
    analysis: DatasetAnalysisResponse;
}

export interface MobileElementMetadata {
    element_type: string;
    x?: number;
    y?: number;
    width?: number;
    height?: number;
    text_content?: string;
    aria_label?: string;
    name?: string;
    keyboard_focusable?: boolean;
    focus_visible?: boolean;
}

export interface MobileAnalyzeRequest {
    platform?: string;
    screen_name?: string;
    image_base64?: string;
    element_metadata?: MobileElementMetadata[];
}

export interface MobileFinding {
    id: number;
    title: string;
    severity: 'high' | 'medium' | 'low' | string;
    category: string;
    description: string;
    evidence: string;
    recommendation: string;
}

export interface MobileCapabilityItem {
    title: string;
    status: string;
    description: string;
}

export interface MobileContextProfile {
    screen_type: string;
    detected_patterns: string[];
    cross_platform_consistency_signal: string;
}

export interface MobileScoreBreakdown {
    mobile_ux: number;
    touch_target: number;
    readability: number;
    layout: number;
    interaction_readiness: number;
}

export interface MobileAnalysisResponse {
    platform: string;
    overall_score: number;
    overview: string;
    ai_interpretation: string;
    ai_mobile_critic: string;
    root_cause_summary: string;
    task_completion_friction: number;
    thumb_zone_summary: string;
    keyboard_overlap_signal: string;
    safe_area_signal: string;
    gesture_friction_summary: string;
    context_playbook: string[];
    cross_platform_parity_summary: string;
    score_breakdown: MobileScoreBreakdown;
    context_profile: MobileContextProfile;
    findings: MobileFinding[];
    supported_now: MobileCapabilityItem[];
    next_phase: MobileCapabilityItem[];
    recommendations: string[];
}

// 🛠️ API Servis Fonksiyonları
export const api = {
    // --- Projects ---
    getProjects: async (): Promise<Project[]> => {
        const response = await apiClient.get<Project[]>('/projects');
        return response.data;
    },

    createProject: async (data: ProjectCreate): Promise<Project> => {
        const response = await apiClient.post<Project>('/projects', data);
        return response.data;
    },

    deleteProject: async (projectId: number): Promise<void> => {
        await apiClient.delete(`/projects/${projectId}`);
    },

    // --- Pages (NEW) ---
    addPage: async (projectId: number, data: { name: string, url: string, description?: string }): Promise<Page> => {
        const response = await apiClient.post<Page>(`/projects/${projectId}/pages`, data);
        return response.data;
    },

    getPages: async (projectId: number): Promise<Page[]> => {
        const response = await apiClient.get<Page[]>(`/projects/${projectId}/pages`);
        return response.data;
    },

    deletePage: async (pageId: number): Promise<void> => {
        await apiClient.delete(`/projects/pages/${pageId}`);
    },

    // --- Test Cases ---
    generateCases: async (data: GenerateCasesRequest): Promise<GenerateCasesResponse> => {
        const response = await apiClient.post<GenerateCasesResponse>('/cases/generate', {
            url: data.url,
            platform: data.platform ?? 'web',
            project_id: data.project_id,
            page_id: data.page_id,
            use_screenshot: data.use_screenshot ?? true,  // Varsayılan: AI ekranı da görsün
            strict_visual: data.strict_visual ?? false,
            require_live_show: data.require_live_show ?? false,
        });
        return response.data;
    },

    getCases: async (projectId?: number, pageId?: number): Promise<TestCase[]> => {
        const params: any = {};
        if (projectId) params.project_id = projectId;
        if (pageId) params.page_id = pageId;
        const response = await apiClient.get<TestCase[]>('/cases/', { params });
        return response.data;
    },

    runTestCase: async (caseId: number): Promise<any> => {
        const response = await apiClient.post(
            `/execution/run-case/${caseId}`,
            {},
            { timeout: 180000 } // 3 dakika: takılmaları sonsuza bırakma
        );
        return response.data;
    },

    startTestCase: async (caseId: number, data?: StartCaseRequest): Promise<RunStartResponse> => {
        const response = await apiClient.post<RunStartResponse>(
            `/execution/start-case/${caseId}`,
            { live_mode: data?.live_mode ?? false }
        );
        return response.data;
    },

    getRunStatus: async (runId: number): Promise<RunStatusResponse> => {
        const response = await apiClient.get<RunStatusResponse>(`/execution/run-status/${runId}`);
        return response.data;
    },

    createTestCase: async (projectId: number, data: Partial<TestCase>): Promise<TestCase> => {
        const response = await apiClient.post(`/projects/${projectId}/cases`, data);
        return response.data;
    },

    updateTestCase: async (caseId: number, data: Partial<TestCase>): Promise<any> => {
        const response = await apiClient.put(`/projects/cases/${caseId}`, data);
        return response.data;
    },

    deleteTestCase: async (caseId: number): Promise<void> => {
        await apiClient.delete(`/projects/cases/${caseId}`);
    },

    // --- Statistics ---
    getDashboardStats: async (): Promise<DashboardStats> => {
        const response = await apiClient.get<DashboardStats>('/stats/dashboard');
        return response.data;
    },

    getProjectStats: async (projectId: number): Promise<any> => {
        const response = await apiClient.get(`/stats/project/${projectId}`);
        return response.data;
    },

    getAlerts: async (): Promise<AlertsResponse> => {
        // Not: Bu endpoint backend'de henüz tam şemalı olmayabilir, 
        // Dashboard beklediği için ekliyoruz veya mock dönebiliriz.
        try {
            const response = await apiClient.get<AlertsResponse>('/stats/alerts');
            return response.data;
        } catch (e) {
            console.warn("Alerts endpoint not ready, returning empty data");
            return { total_alerts: 0, critical_count: 0, warning_count: 0, alerts: [] };
        }
    },

    analyzeAccessibilityImage: async (imageBase64: string, platform = 'web'): Promise<AccessibilityAnalysisResponse> => {
        const response = await apiClient.post<AccessibilityAnalysisResponse>('/accessibility/analyze-image', {
            platform,
            image_base64: imageBase64,
        });
        return response.data;
    },

    analyzeAccessibilityUrl: async (data: AccessibilityUrlAnalysisRequest): Promise<AccessibilityAnalysisResponse> => {
        const response = await apiClient.post<AccessibilityAnalysisResponse>('/accessibility/analyze-url', {
            url: data.url,
            platform: data.platform ?? 'web',
            headless: data.headless ?? true,
            full_page: data.full_page ?? true,
        });
        return response.data;
    },

    analyzeUiuxImage: async (imageBase64: string, platform = 'web'): Promise<UiuxAnalysisResponse> => {
        const response = await apiClient.post<UiuxAnalysisResponse>('/uiux/analyze-image', {
            platform,
            image_base64: imageBase64,
        });
        return response.data;
    },

    getUiuxHistory: async (limit = 8): Promise<UiuxHistoryItem[]> => {
        const response = await apiClient.get<UiuxHistoryItem[]>('/uiux/history', {
            params: { limit },
        });
        return response.data;
    },

    getUiuxHistoryDetail: async (recordId: number): Promise<UiuxHistoryDetail> => {
        const response = await apiClient.get<UiuxHistoryDetail>(`/uiux/history/${recordId}`);
        return response.data;
    },

    updateUiuxHistory: async (recordId: number, data: UiuxHistoryUpdateRequest): Promise<UiuxHistoryItem> => {
        const response = await apiClient.patch<UiuxHistoryItem>(`/uiux/history/${recordId}`, data);
        return response.data;
    },

    deleteUiuxHistory: async (recordId: number): Promise<void> => {
        await apiClient.delete(`/uiux/history/${recordId}`);
    },

    analyzeSecurityImage: async (imageBase64: string, platform = 'web'): Promise<SecurityAnalysisResponse> => {
        const response = await apiClient.post<SecurityAnalysisResponse>('/security/analyze-image', {
            platform,
            image_base64: imageBase64,
        });
        return response.data;
    },

    analyzeSecurityUrl: async (data: SecurityUrlAnalysisRequest): Promise<SecurityAnalysisResponse> => {
        const response = await apiClient.post<SecurityAnalysisResponse>('/security/analyze-url', {
            url: data.url,
            platform: data.platform ?? 'web',
            headless: data.headless ?? true,
            full_page: data.full_page ?? true,
        });
        return response.data;
    },

    simulateSecurityUrl: async (data: SecuritySimulationRequest): Promise<SecuritySimulationResponse> => {
        const response = await apiClient.post<SecuritySimulationResponse>('/security/simulate-url', {
            url: data.url,
            platform: data.platform ?? 'web',
            hypotheses: data.hypotheses ?? [],
        });
        return response.data;
    },

    getSecurityHistory: async (limit = 8): Promise<SecurityHistoryItem[]> => {
        const response = await apiClient.get<SecurityHistoryItem[]>('/security/history', {
            params: { limit },
        });
        return response.data;
    },

    getSecurityHistoryDetail: async (recordId: number): Promise<SecurityHistoryDetail> => {
        const response = await apiClient.get<SecurityHistoryDetail>(`/security/history/${recordId}`);
        return response.data;
    },

    updateSecurityHistory: async (recordId: number, data: SecurityHistoryUpdateRequest): Promise<SecurityHistoryItem> => {
        const response = await apiClient.patch<SecurityHistoryItem>(`/security/history/${recordId}`, data);
        return response.data;
    },

    deleteSecurityHistory: async (recordId: number): Promise<void> => {
        await apiClient.delete(`/security/history/${recordId}`);
    },

    getProjectSummaryReport: async (projectId: number): Promise<ProjectSummaryReport> => {
        const response = await apiClient.get<ProjectSummaryReport>(`/reports/project/${projectId}/summary`);
        return response.data;
    },

    getAccessibilityHistory: async (limit = 8): Promise<AccessibilityHistoryItem[]> => {
        const response = await apiClient.get<AccessibilityHistoryItem[]>('/accessibility/history', {
            params: { limit },
        });
        return response.data;
    },

    getAccessibilityHistoryDetail: async (recordId: number): Promise<AccessibilityHistoryDetail> => {
        const response = await apiClient.get<AccessibilityHistoryDetail>(`/accessibility/history/${recordId}`);
        return response.data;
    },

    updateAccessibilityHistory: async (recordId: number, data: AccessibilityHistoryUpdateRequest): Promise<AccessibilityHistoryItem> => {
        const response = await apiClient.patch<AccessibilityHistoryItem>(`/accessibility/history/${recordId}`, data);
        return response.data;
    },

    deleteAccessibilityHistory: async (recordId: number): Promise<void> => {
        await apiClient.delete(`/accessibility/history/${recordId}`);
    },

    analyzeApiRequest: async (data: ApiTestAnalyzeRequest): Promise<ApiTestAnalyzeResponse> => {
        const response = await apiClient.post<ApiTestAnalyzeResponse>('/api-test/analyze', {
            method: data.method,
            url: data.url,
            project_id: data.project_id,
            headers: data.headers ?? {},
            body: data.body ?? null,
            params: data.params ?? null,
            expected_status: data.expected_status,
            expected_fields: data.expected_fields ?? [],
            expected_response_type: data.expected_response_type,
            run_negative_checks: data.run_negative_checks ?? true,
        });
        return response.data;
    },

    getApiHistory: async (limit = 12): Promise<ApiHistoryItem[]> => {
        const response = await apiClient.get<ApiHistoryItem[]>('/api-test/history', {
            params: { limit },
        });
        return response.data;
    },

    getApiHistoryDetail: async (recordId: number): Promise<ApiHistoryDetail> => {
        const response = await apiClient.get<ApiHistoryDetail>(`/api-test/history/${recordId}`);
        return response.data;
    },

    analyzeDbQuality: async (data: DbQualityRequest): Promise<DbQualityResponse> => {
        const response = await apiClient.post<DbQualityResponse>('/db-test/quality-audit', {
            connection_string: data.connection_string,
            query: data.query,
            table_name: data.table_name,
            expected_columns: data.expected_columns ?? [],
            api_expected_fields: data.api_expected_fields ?? [],
            sample_limit: data.sample_limit ?? 50,
        });
        return response.data;
    },

    getDbHistory: async (limit = 12): Promise<DbHistoryItem[]> => {
        const response = await apiClient.get<DbHistoryItem[]>('/db-test/history', {
            params: { limit },
        });
        return response.data;
    },

    getDbHistoryDetail: async (recordId: number): Promise<DbHistoryDetail> => {
        const response = await apiClient.get<DbHistoryDetail>(`/db-test/history/${recordId}`);
        return response.data;
    },

    analyzePerformance: async (data: PerformanceAnalyzeRequest): Promise<PerformanceAnalysisResponse> => {
        const response = await apiClient.post<PerformanceAnalysisResponse>('/performance/analyze', {
            url: data.url,
            api_url: data.api_url,
            project_id: data.project_id,
            api_method: data.api_method ?? 'GET',
            db_connection_string: data.db_connection_string,
            db_query: data.db_query,
            sample_api_runs: data.sample_api_runs ?? 5,
            platform: data.platform ?? 'web',
        });
        return response.data;
    },

    getPerformanceHistory: async (limit = 12): Promise<PerformanceHistoryItem[]> => {
        const response = await apiClient.get<PerformanceHistoryItem[]>('/performance/history', {
            params: { limit },
        });
        return response.data;
    },

    getPerformanceHistoryDetail: async (recordId: number): Promise<PerformanceHistoryDetail> => {
        const response = await apiClient.get<PerformanceHistoryDetail>(`/performance/history/${recordId}`);
        return response.data;
    },

    analyzeDataset: async (data: DatasetAnalyzePayload): Promise<DatasetAnalysisResponse> => {
        const response = await apiClient.post<DatasetAnalysisResponse>('/dataset/analyze', data);
        return response.data;
    },

    analyzeDatasetZip: async (file: File): Promise<DatasetAnalysisResponse> => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await axios.post<DatasetAnalysisResponse>(`${backendBaseUrl}/dataset/upload-analyze`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 180000,
        });
        return response.data;
    },

    getDatasetHistory: async (limit = 20): Promise<DatasetHistoryItem[]> => {
        const response = await apiClient.get<DatasetHistoryItem[]>('/dataset/history', {
            params: { limit },
        });
        return response.data;
    },

    getDatasetHistoryDetail: async (recordId: number): Promise<DatasetHistoryDetail> => {
        const response = await apiClient.get<DatasetHistoryDetail>(`/dataset/history/${recordId}`);
        return response.data;
    },

    createDatasetJiraTicket: async (data: DatasetAnalysisResponse): Promise<DatasetTicketResponse> => {
        const response = await apiClient.post<DatasetTicketResponse>('/dataset/tickets/jira', data);
        return response.data;
    },

    analyzeMobile: async (data: MobileAnalyzeRequest): Promise<MobileAnalysisResponse> => {
        const response = await apiClient.post<MobileAnalysisResponse>('/mobile/analyze', {
            platform: data.platform ?? 'android',
            screen_name: data.screen_name,
            image_base64: data.image_base64,
            element_metadata: data.element_metadata ?? [],
        });
        return response.data;
    },
};
