import axios from 'axios';

// 🌐 Axios Instance (Base Config)
const apiClient = axios.create({
    baseURL: '/api', // Vite proxy sayesinde backend'e gider
    headers: {
        'Content-Type': 'application/json',
    },
});

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
    cross_module_hints: SecurityCrossModuleHint[];
    recommendations: string[];
}

export interface SecurityUrlAnalysisRequest {
    url: string;
    platform?: string;
    headless?: boolean;
    full_page?: boolean;
}

export interface ApiTestAnalyzeRequest {
    method: string;
    url: string;
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

export interface ApiCrossModuleCorrelation {
    module: string;
    summary: string;
    reason: string;
    suggested_follow_up: string;
}

export interface ApiTestAnalyzeResponse {
    method: string;
    url: string;
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
    findings: ApiTestFinding[];
    negative_checks: ApiNegativeCheck[];
    generated_tests: ApiGeneratedTest[];
    cross_module_correlation: ApiCrossModuleCorrelation[];
    raw_result: Record<string, any>;
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
            strict_visual: data.strict_visual ?? true,    // Varsayılan: hayali fallback kapalı
            require_live_show: data.require_live_show ?? true, // Varsayılan: canlı bridge zorunlu
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
};
