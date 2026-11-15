"use client";
// app/dashboard/teachers/page.tsx — Teachers management page
import { useQuery } from "@tanstack/react-query";
import { schoolApi, type Teacher } from "@/lib/api";
import toast from "react-hot-toast";

// ── Subject colors ────────────────────────────────────────────────────────────
const SUBJECT_COLORS: Record<string, string> = {
  science: "#10B981",
  maths: "#8B5CF6",
  hindi: "#EF4444",
  english: "#3B82F6",
  sst: "#F59E0B",
  gk: "#06B6D4",
};

export default function TeachersPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["school-teachers"],
    queryFn: () => schoolApi.getTeachers().then((r) => r.data?.data || r.data),
  });

  if (isLoading) return <TeachersSkeleton />;
  if (error || !data) return <ErrorState />;

  const teachers = data.teachers || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* ── Page Header ─────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-lg shadow-lg"
              style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
            >
              👨‍🏫
            </div>
            <h1 className="text-2xl font-bold text-white">Teachers</h1>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Manage your school&apos;s teaching staff
          </p>
        </div>
        <button
          disabled
          className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white/50 bg-slate-700/50 border border-white/5 cursor-not-allowed"
          title="Coming soon"
          onClick={() => toast("Invite feature coming soon!")}
        >
          + Invite Teacher
        </button>
      </div>

      {/* ── Stats Row ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-5">
          <p className="text-xs font-medium text-slate-400">Total Teachers</p>
          <p className="text-3xl font-bold mt-1.5 font-mono text-blue-400">
            {teachers.length}
          </p>
        </div>
        <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-5">
          <p className="text-xs font-medium text-slate-400">Active Now</p>
          <p className="text-3xl font-bold mt-1.5 font-mono text-emerald-400">
            {teachers.filter((t) => t.last_login).length}
          </p>
        </div>
        <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-5 col-span-2 lg:col-span-1">
          <p className="text-xs font-medium text-slate-400">Content Uploaded</p>
          <p className="text-3xl font-bold mt-1.5 font-mono text-violet-400">
            {teachers.reduce((sum, t) => sum + (t.content_uploaded || 0), 0)}
          </p>
        </div>
      </div>

      {/* ── Teachers Grid ───────────────────────────────────────────── */}
      {teachers.length === 0 ? (
        <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-12 text-center">
          <span className="text-4xl mb-4 block">👨‍🏫</span>
          <p className="text-white font-semibold">No teachers yet</p>
          <p className="text-sm text-slate-400 mt-1">
            Teachers will appear here once they join your school
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {teachers.map((teacher) => (
            <TeacherCard key={teacher.teacher_id} teacher={teacher} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Teacher Card Component ────────────────────────────────────────────────────
function TeacherCard({ teacher }: { teacher: Teacher }) {
  const initials = teacher.display_name
    ? teacher.display_name.charAt(0).toUpperCase()
    : teacher.email.charAt(0).toUpperCase();

  const isActive = !!teacher.last_login;

  return (
    <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-5 hover:border-white/10 transition-all group">
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-white text-lg font-bold shrink-0 shadow-lg">
          {initials}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-white font-semibold text-sm truncate">
              {teacher.display_name || "Unnamed Teacher"}
            </h3>
            {/* Active status indicator */}
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                isActive ? "bg-emerald-400" : "bg-slate-600"
              }`}
              title={isActive ? "Active" : "Inactive"}
            />
          </div>
          <p className="text-xs text-slate-400 truncate mt-0.5">{teacher.email}</p>

          {/* Role badge */}
          <div className="flex items-center gap-2 mt-2">
            <span className="px-2 py-0.5 rounded-md text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 capitalize">
              {teacher.role || "teacher"}
            </span>
            {teacher.trusted_devices > 0 && (
              <span className="text-xs text-slate-500">
                {teacher.trusted_devices} device{teacher.trusted_devices > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Subject badges */}
      {teacher.subjects && teacher.subjects.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-4">
          {teacher.subjects.map((subject) => {
            const color = SUBJECT_COLORS[subject.toLowerCase()] || "#94A3B8";
            return (
              <span
                key={subject}
                className="px-2.5 py-1 rounded-lg text-xs font-medium capitalize"
                style={{
                  background: `${color}15`,
                  color: color,
                  border: `1px solid ${color}30`,
                }}
              >
                {subject}
              </span>
            );
          })}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/5">
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <span>📄</span>
          <span>{teacher.content_uploaded || 0} uploads</span>
        </div>
        <div className="text-xs text-slate-500">
          {teacher.last_login
            ? `Last login: ${new Date(teacher.last_login).toLocaleDateString()}`
            : "Never logged in"}
        </div>
      </div>
    </div>
  );
}

// ── Loading Skeleton ──────────────────────────────────────────────────────────
function TeachersSkeleton() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-pulse">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-slate-700" />
        <div className="h-7 bg-slate-700 rounded-lg w-40" />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-slate-800/50 rounded-2xl border border-white/5 p-5 h-24">
            <div className="h-3 bg-slate-700 rounded w-24 mb-3" />
            <div className="h-8 bg-slate-700 rounded w-12" />
          </div>
        ))}
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-slate-800/50 rounded-2xl border border-white/5 p-5 h-48">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-slate-700" />
              <div className="flex-1">
                <div className="h-4 bg-slate-700 rounded w-32 mb-2" />
                <div className="h-3 bg-slate-700/50 rounded w-40" />
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <div className="h-6 bg-slate-700/50 rounded-lg w-16" />
              <div className="h-6 bg-slate-700/50 rounded-lg w-16" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Error State ───────────────────────────────────────────────────────────────
function ErrorState() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <div className="w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center text-3xl bg-amber-500/10 border border-amber-500/20">
          ⚠️
        </div>
        <p className="font-semibold text-white">Failed to load teachers</p>
        <p className="text-sm text-slate-400 mt-1">
          Check your connection or try refreshing
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 rounded-xl text-sm font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 transition-colors"
        >
          Refresh Page
        </button>
      </div>
    </div>
  );
}
