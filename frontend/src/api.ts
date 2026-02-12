import axios from 'axios';

// Backend URL (Environment Variable or Default)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

export const startScan = async (targetUrl: string): Promise<ScanResponse> => {
    const response = await api.post<ScanResponse>("/scan", { target_url: targetUrl });
    return response.data;
};

export const getScanStatus = async (scanId: string): Promise<ScanResponse> => {
    const response = await api.get<ScanResponse>(`/scan/${scanId}`);
    return response.data;
};
