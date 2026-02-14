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
        // Global hata yönetimi (örn: 401 ise logout yap)
        console.error("API Hatası:", error.response?.data || error.message);
        return Promise.reject(error);
    }
);

// 📦 Veri Tipleri (Backend Modelim)
export interface Project {
    id: number;
    name: string;
    description?: string;
    platforms: string[]; // ["WEB", "MOBILE_ANDROID"]
    created_at: string;
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
}

export interface TestCase {
    id: number;
    project_id: number;
    title: string;
    description?: string;
    status: 'draft' | 'approved' | 'archived';
    priority: string;
    steps: TestStep[];
}

export interface GenerateCasesResponse {
    message: string;
    cases: TestCase[];
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

    // --- Tests ---
    generateCases: async (projectId: number): Promise<TestCase[]> => {
        const response = await apiClient.post<GenerateCasesResponse>(`/projects/${projectId}/generate-cases`);
        return response.data.cases;
    },

    runTestCase: async (caseId: number): Promise<any> => {
        const response = await apiClient.post(`/execution/run-case/${caseId}`);
        return response.data;
    },

    getHealth: async () => {
        return apiClient.get('/health');
    }
};

export interface TestExecutionResult {
    case_id: number;
    status: 'completed' | 'crashed';
    steps: {
        order: number;
        action: string;
        status: 'passed' | 'failed' | 'pending';
        error?: string;
    }[];
    error?: string;
}
