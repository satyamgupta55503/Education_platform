// lib/api.ts  — Axios client connecting Next.js → FastAPI backend

import axios, { AxiosInstance, AxiosError } from "axios";
import Cookies from "js-cookie";

// ─── Config ───────────────────────────────────────────────────────────────────
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ─── Axios instance ───────────────────────────────────────────────────────────
const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// Auto-attach token
api.interceptors.request.use((config) => {
  const token = Cookies.get("teacher_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 401 → redirect to login
api.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      Cookies.remove("teacher_token");
      if (typeof window !== "undefined") window.location.href = "/auth/login";
    }
    return Promise.reject(err);
  }
);

export default api;

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  sendOTP: (email: string, workspaceId: string) =>
    api.post("/auth/teacher/otp/send", { email, workspace_id: workspaceId }),

  verifyOTP: (
    email: string, workspaceId: string, otpCode: string,
    deviceFingerprint: string, deviceName: string
  ) =>
    api.post("/auth/teacher/otp/verify", {
      email, workspace_id: workspaceId, otp_code: otpCode,
      device_fingerprint: deviceFingerprint, device_name: deviceName,
    }),

  getTOTPSetup: (teacherId: string, email: string) =>
    api.get("/auth/teacher/totp/setup", { params: { teacher_id: teacherId, email } }),

  verifyTOTP: (teacherId: string, workspaceId: string, totpCode: string,
    deviceFingerprint: string, deviceName: string) =>
    api.post("/auth/teacher/totp/verify", {
      teacher_id: teacherId, workspace_id: workspaceId, totp_code: totpCode,
      device_fingerprint: deviceFingerprint, device_name: deviceName,
    }),

  logout: () => api.post("/auth/logout"),
};

// ─── School Dashboard ─────────────────────────────────────────────────────────
export const schoolApi = {
  getOverview: () =>
    api.get<SchoolOverviewResponse>("/school/dashboard/overview"),

  getStudents: (params?: StudentsParams) =>
    api.get<StudentsResponse>("/school/dashboard/students", { params }),

  getTeachers: () =>
    api.get<TeachersResponse>("/school/dashboard/teachers"),

  getSubjects: () =>
    api.get<SubjectsResponse>("/school/dashboard/subjects"),

  getWeakStudents: (threshold = 0.4) =>
    api.get<WeakStudentsResponse>("/school/dashboard/weak-students", {
      params: { threshold },
    }),

  getContentUsage: () =>
    api.get<ContentUsageResponse>("/school/dashboard/content-usage"),
};

// ─── Content ──────────────────────────────────────────────────────────────────
export const contentApi = {
  list: (params?: ContentListParams) =>
    api.get<ContentListResponse>("/school/content/list", { params }),

  uploadPDF: (formData: FormData) =>
    api.post("/school/content/upload/pdf", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  uploadVideo: (youtubeUrl: string, subject: string, grade: number,
    workspaceId?: string) =>
    api.post("/school/content/upload/video", {
      youtube_url: youtubeUrl, subject, grade, workspace_id: workspaceId,
    }),
};

// ─── Types ────────────────────────────────────────────────────────────────────
export interface SchoolOverviewResponse {
  status: string;
  workspace: {
    workspace_id: string; school_name: string; school_code: string;
    plan_type: string; monthly_quota: number; tokens_used: number;
    quota_used_pct: number; is_active: boolean;
  };
  team: { teacher_count: number; content_pieces: number; total_chunks: number };
  today: { active_users: number; sessions: number; messages: number };
  cache: { hit_rates_7d: Record<string, { count: number; pct: number }> };
  subject_engagement: SubjectEngagement[];
  activity_30d: ActivityDay[];
}

export interface SubjectEngagement {
  subject: string; content_pieces: number; total_chunks: number;
  videos: number; pdfs: number;
}

export interface ActivityDay { date: string; sessions: number; messages: number }

export interface Student {
  user_id: string; educat_id: string; display_name: string; grade: number;
  language: string; tier: string; brain_coins: number; streak_days: number;
  last_active: string | null; overall_mastery_pct: number; total_sessions: number;
  created_at: string;
}

export interface StudentsParams {
  grade?: number; sort_by?: string; order?: string; page?: number; limit?: number;
}
export interface StudentsResponse {
  students: Student[]; total: number; page: number; pages: number;
}

export interface Teacher {
  teacher_id: string; display_name: string; email: string; role: string;
  subjects: string[]; last_login: string | null; content_uploaded: number;
  trusted_devices: number;
}
export interface TeachersResponse { teachers: Teacher[] }

export interface SubjectStat {
  subject: string; content_pieces: number; total_chunks: number;
  videos: number; pdfs: number; total_sessions: number;
  unique_students: number; total_messages: number; avg_mastery_pct: number;
}
export interface SubjectsResponse { subjects: SubjectStat[] }

export interface WeakStudent {
  user_id: string; educat_id: string; display_name: string; grade: number;
  streak_days: number; avg_mastery_pct: number; weak_topics_count: number;
}
export interface WeakStudentsResponse { weak_students: WeakStudent[]; threshold_pct: number }

export interface ContentChunk {
  chunk_id: string; subject: string; grade: number; preview: string;
  source_type: string; alpha_score: number; beta_score: number;
  engagement_rate: number; content_title: string;
}
export interface ContentUsageResponse {
  top_content: ContentChunk[]; low_engagement: ContentChunk[];
}

export interface ContentItem {
  content_id: string; subject: string; grade: number; title: string;
  content_type: string; source_type: string; chunk_count: number; created_at: string;
}
export interface ContentListParams { subject?: string; grade?: number; page?: number; limit?: number }
export interface ContentListResponse { content: ContentItem[] }
