import axios from 'axios';

// Backend URL (Environment Variable or Default)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

export interface ScanResult {
    target: string;
    alerts_count: number;
    ai_analysis: string;
}

export const startScan = async (targetUrl: string): Promise<ScanResult> => {
    const response = await api.post<ScanResult>("/scan", { target_url: targetUrl });
    return response.data;
};
