const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export interface User {
  id: number;
  name: string;
  email: string;
}

export interface IndicatorScore {
  name: string;
  score: number;
  max_score: number;
  detail: string;
}

export interface PricePoint {
  date: string;
  close: number;
  volume?: number;
}

export interface MarketContext {
  company_name?: string;
  current_price?: number;
  volume_spike_ratio?: number;
  daily_return_std?: number;
  institutional_ownership_pct?: number;
  recent_price_change_pct?: number;
  market_cap?: number;
  avg_volume_3d?: number;
  avg_volume_30d?: number;
  price_series?: PricePoint[];
}

export interface Analysis {
  id: number;
  stock_symbol: string;
  risk_score: number;
  risk_level: "green" | "red";
  explanation: string;
  indicators: IndicatorScore[];
  created_at: string;
  market_context?: MarketContext;
}

export interface AnalysisSummary {
  id: number;
  stock_symbol: string;
  risk_score: number;
  risk_level: "green" | "red";
  created_at: string;
}

export interface ScoreBucket {
  label: string;
  count: number;
}

export interface TimelinePoint {
  date: string;
  score: number;
  stock_symbol: string;
  risk_level: string;
}

export interface SymbolStat {
  stock_symbol: string;
  count: number;
  avg_score: number;
  latest_level: string;
  latest_score: number;
}

export interface IndicatorAverage {
  name: string;
  avg_score: number;
  max_score: number;
}

export interface AnalysisStats {
  total: number;
  red_count: number;
  green_count: number;
  avg_score: number;
  score_buckets: ScoreBucket[];
  timeline: TimelinePoint[];
  by_symbol: SymbolStat[];
  indicator_averages: IndicatorAverage[];
}

export interface NotionHealth {
  configured: boolean;
  connected: boolean;
  database_title?: string;
  error?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
}

export function setUser(user: User) {
  localStorage.setItem("user", JSON.stringify(user));
}

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    if (res.status === 401 && typeof window !== "undefined") {
      clearToken();
      window.location.href = "/login";
    }
    throw new ApiError(res.status, body.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  register: (name: string, email: string, password: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  analyze: (symbol: string) =>
    request<Analysis>("/analysis", {
      method: "POST",
      body: JSON.stringify({ symbol }),
    }),

  history: (skip = 0, limit = 20) =>
    request<{ items: AnalysisSummary[]; total: number }>(
      `/analysis/history?skip=${skip}&limit=${limit}`
    ),

  stats: () => request<AnalysisStats>("/analysis/stats"),

  notionHealth: () => request<NotionHealth>("/health/notion"),

  getAnalysis: (id: number) => request<Analysis>(`/analysis/${id}`),

  notionStocks: () =>
    request<{ items: AnalysisSummary[]; total: number }>("/analysis/notion-stocks"),
};
