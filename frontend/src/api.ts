import axios from 'axios';

// Backend URL (Environment Variable or Default)
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

// Scan Response (Async)
export interface ScanResponse {
    scan_id: string;
    status: "pending" | "completed" | "failed";
    target: string;
    agent_response?: string;
}

export const startScan = async (targetUrl: string, language: string = "en"): Promise<ScanResponse> => {
    const response = await api.post<ScanResponse>("/scan", { target_url: targetUrl, language });
    return response.data;
};

// --- User Feedback API ---
export const submitFeedback = async (
    scanId: string,
    vulnerability: string,
    isAccurate: boolean,
    comments: string = ""
) => {
    const response = await api.post("/feedback", {
        scan_id: scanId,
        vulnerability_name: vulnerability,
        is_accurate: isAccurate,
        comments: comments,
    });
    return response.data;
};

// --- Model Metrics API ---
export const getModelMetrics = async () => {
    const response = await api.get("/models/metrics");
    return response.data;
};

// --- GitHub Integration API (Session-based) ---
export interface GitHubRepo {
    id: number;
    name: string;
    full_name: string;
    html_url: string;
    description?: string;
    private: boolean;
    language?: string;
}

export interface GitHubUser {
    github_user: string;
    github_id: number;
    avatar_url?: string;
    session_id: string;
}

// 현재 로그인된 유저 정보 조회
export const getCurrentUser = async (sessionId: string): Promise<GitHubUser> => {
    const response = await api.get<GitHubUser>("/auth/me", {
        params: { session_id: sessionId },
    });
    return response.data;
};

// 유저 리포지토리 목록 (session_id 기반)
export const getUserRepos = async (sessionId: string): Promise<GitHubRepo[]> => {
    const response = await api.get<GitHubRepo[]>("/user/repos", {
        params: { session_id: sessionId },
    });
    return response.data;
};

// 로그아웃
export const logout = async (sessionId: string) => {
    const response = await api.post("/auth/logout", null, {
        params: { session_id: sessionId },
    });
    return response.data;
};

export const getScanStatus = async (scanId: string): Promise<ScanResponse> => {
    const response = await api.get<ScanResponse>(`/scan/${scanId}`);
    return response.data;
};

