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

export interface GenerateCasesResponse {
    message: string;
    cases: TestCase[];
}

export interface DashboardStats {
    total_projects: number;
    total_cases: number;
    recent_runs: number;
    success_rate: number;
    platform_breakdown: any[];
    recent_test_runs: any[];
    weekly_trend: any[];
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
    generateCasesForPage: async (pageId: number): Promise<GenerateCasesResponse> => {
        const response = await apiClient.post<GenerateCasesResponse>(`/projects/pages/${pageId}/generate-cases`);
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
        const response = await apiClient.post(`/execution/run-case/${caseId}`);
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
    }
};
