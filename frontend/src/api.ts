import axios from 'axios';

// Railway Backend URL (Hardcoded for MVP, better to use env)
const API_BASE_URL = "https://redeye-production.up.railway.app";

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
