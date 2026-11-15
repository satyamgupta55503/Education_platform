// lib/api.ts  — Admin dashboard Axios client
import axios, { AxiosInstance, AxiosError } from "axios";
import Cookies from "js-cookie";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const api: AxiosInstance = axios.create({
  baseURL: API_BASE, timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((cfg) => {
  const tok = Cookies.get("admin_token");
  if (tok) cfg.headers.Authorization = `Bearer ${tok}`;
  return cfg;
});
api.interceptors.response.use(
  (r) => r,
  (e: AxiosError) => {
    if (e.response?.status === 401) {
      Cookies.remove("admin_token");
      if (typeof window !== "undefined") window.location.href = "/auth/login";
    }
    return Promise.reject(e);
  }
);
export default api;

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  sendOTP:    (email: string) =>
    api.post("/auth/admin/otp/send", { email }),
  verifyOTP:  (email: string, otpCode: string) =>
    api.post("/auth/admin/otp/verify", { email, otp_code: otpCode }),
  verifyTOTP: (adminId: string, totpCode: string) =>
    api.post("/auth/admin/totp/verify", { admin_id: adminId, totp_code: totpCode }),
  logout:     () => api.post("/auth/logout"),
};

// ── Admin Dashboard APIs ─────────────────────────────────────────────────────
export const adminApi = {
  getOverview:   () => api.get<AdminOverview>("/admin/dashboard/overview"),
  getSchools:    (p?: { plan_type?: string; page?: number }) =>
    api.get<SchoolsResponse>("/admin/dashboard/schools", { params: p }),
  getRevenue:    (months = 6) =>
    api.get<RevenueResponse>("/admin/dashboard/revenue", { params: { months } }),
  getCacheHealth: () => api.get<CacheHealth>("/admin/dashboard/cache-health"),
  getAlerts:     () => api.get<AlertsResponse>("/admin/dashboard/alerts"),

  // CRUD
  createWorkspace: (data: WorkspaceCreate) =>
    api.post("/admin/workspaces", data),
  updateUserTier:  (userId: string, tier: string) =>
    api.patch(`/admin/users/${userId}/tier`, null, { params: { tier } }),
  listUsers:       (p?: { tier?: string; grade?: number; page?: number }) =>
    api.get<UsersResponse>("/admin/users", { params: p }),
  listContent:     (p?: { subject?: string; grade?: number }) =>
    api.get("/content/list", { params: p }),
};

// ── Types ─────────────────────────────────────────────────────────────────────
export interface AdminOverview {
  status: string;
  users: {
    total: number;
    by_tier: Record<string, number>;
    growth_30d: { date: string; new_users: number }[];
  };
  today: { dau: number; sessions: number; messages: number; tokens_used: number };
  this_week: { wau: number; sessions: number; tokens_used: number };
  schools: { total: number; by_plan: { plan_type: string; count: number; total_tokens_used: number }[] };
  cache: {
    semantic_cache_size: number;
    hit_rates_7d: Record<string, { count: number; pct: number }>;
    redis_memory: { used_memory_mb: number; peak_memory_mb: number };
  };
  content: {
    total_pieces: number;
    by_subject: { subject: string; pieces: number; chunks: number }[];
  };
}

export interface School {
  workspace_id: string; school_name: string; school_code: string;
  plan_type: string; monthly_quota: number; tokens_used: number;
  quota_used_pct: number; state: string; city: string;
  contact_email: string; created_at: string; expires_at: string | null;
  teachers: number; content_pieces: number;
}
export interface SchoolsResponse { schools: School[]; total: number; page: number; pages: number }

export interface RevenueRow {
  month: string; tier: string; subscriptions: number; revenue_inr: number;
}
export interface RevenueResponse {
  monthly_revenue: RevenueRow[];
  total_active: { total_inr: number; total_subs: number };
}

export interface CacheHealth {
  l1_redis: { key_count: number };
  l2_semantic: {
    by_subject_grade: {
      subject: string; grade: number; entries: number;
      total_hits: number; avg_hits_per_entry: number;
    }[];
  };
  audio_cache: { by_language: { language: string; entries: number; total_size_kb: number }[] };
}

export interface SystemAlert {
  level: "critical" | "warning" | "info";
  metric: string; message: string; action: string;
}
export interface AlertsResponse {
  alerts: SystemAlert[];
  total: number; critical: number; warnings: number; timestamp: string;
}

export interface User {
  user_id: string; grade: number; language: string; tier: string;
  brain_coins: number; streak_days: number;
  tokens_remaining_monthly: number; created_at: string;
}
export interface UsersResponse { users: User[] }

export interface WorkspaceCreate {
  school_name: string; school_code: string; plan_type: string;
  max_teachers: number; monthly_quota: number;
  contact_email: string; state: string; city: string;
}
