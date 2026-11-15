"use client";
// app/dashboard/overview/page.tsx — Modern dark-themed school dashboard overview
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Cookies from "js-cookie";
import { schoolApi, type SchoolOverviewResponse } from "@/lib/api";

// ── Subject colors for engagement bars ────────────────────────────────────────
const SUBJECT_COLORS: Record<string, string> = {
  science: "#10B981",
  maths: "#8B5CF6",
  hindi: "#EF4444",
  english: "#3B82F6",
  sst: "#F59E0B",
  gk: "#06B6D4",
};

const SUBJECT_EMOJIS: Record<string, string> = {
  science: "🔬",
  maths: "📐",
  hindi: "🔤",
  english: "📖",
  sst: "🌍",
  gk: "🌟",
};

export default function OverviewPage() {
  const [teacherName, setTeacherName] = useState("Teacher");

  useEffect(() => {
    setTeacherName(Cookies.get("teacher_name") || "Teacher");
  }, []);

  const { data, isLoading, error } = useQuery({
    queryKey: ["school-overview"],
    queryFn: () => schoolApi.getOverview().then((r) => r.data?.data || r.data),
    refetchInterval: 60_000,
  });

  if (isLoading) return <OverviewSkeleton />;
  if (error || !data) return <ErrorState />;

  const { workspace, team, today, subject_engagement, activity_30d } = data;

  // Calculate max for bar chart scaling
  const maxChunks = Math.max(...(subject_engagement?.map((s) => s.total_chunks) || [1]));
  const maxActivity = Math.max(...(activity_30d?.map((d) => d.sessions + d.messages) || [1]));

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
              🐱
            </div>
            <h1 className="text-2xl font-bold text-white">EduCat AI School Portal</h1>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Welcome, <span className="text-blue-400 font-semibold">{teacherName}</span>! 👋
          </p>
        </div>
        <div className="flex items-center gap-2">
          {workspace && (
            <span className="px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {workspace.school_name}
            </span>
          )}
        </div>
      </div>

      {/* ── Stats Cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Students"
          value={today?.active_users?.toString() || "0"}
          sub="Registered in system"
          color="#3B82F6"
          emoji="👥"
          delay={1}
        />
        <StatCard
          label="Active Today"
          value={today?.sessions?.toString() || "0"}
          sub={`${today?.messages || 0} messages`}
          color="#10B981"
          emoji="🟢"
          delay={2}
        />
        <StatCard
          label="Sessions"
          value={today?.sessions?.toString() || "0"}
          sub="Today's learning sessions"
          color="#8B5CF6"
          emoji="📚"
          delay={3}
        />
        <StatCard
          label="Content Pieces"
          value={team?.content_pieces?.toString() || "0"}
          sub={`${team?.total_chunks?.toLocaleString() || 0} chunks`}
          color="#F59E0B"
          emoji="📄"
          delay={4}
        />
      </div>

      {/* ── Quick Actions ───────────────────────────────────────────── */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Quick Actions</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <QuickAction emoji="🎓" label="Start Live Lesson" color="#3B82F6" href="/dashboard/live" />
          <QuickAction emoji="👥" label="View Students" color="#10B981" href="/dashboard/students" />
          <QuickAction emoji="📤" label="Upload Content" color="#8B5CF6" href="/dashboard/content" />
          <QuickAction emoji="📈" label="Analytics" color="#F59E0B" href="/dashboard/analytics" />
        </div>
      </div>

      {/* ── Subject Engagement Chart ────────────────────────────────── */}
      {subject_engagement && subject_engagement.length > 0 && (
        <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-semibold text-white">Subject Engagement</h2>
              <p className="text-xs text-slate-500 mt-0.5">Content pieces by subject</p>
            </div>
            <span className="text-2xl">📊</span>
          </div>
          <div className="space-y-3">
            {subject_engagement.map((subject) => {
              const pct = maxChunks > 0 ? (subject.total_chunks / maxChunks) * 100 : 0;
              const color = SUBJECT_COLORS[subject.subject] || "#94A3B8";
              const emoji = SUBJECT_EMOJIS[subject.subject] || "📚";
              return (
                <div key={subject.subject} className="group">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{emoji}</span>
                      <span className="text-sm font-medium text-slate-300 capitalize">
                        {subject.subject}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <span>{subject.videos} videos</span>
                      <span>{subject.pdfs} PDFs</span>
                      <span className="font-semibold text-slate-300 font-mono">
                        {subject.total_chunks} chunks
                      </span>
                    </div>
                  </div>
                  <div className="h-3 rounded-full bg-slate-700/50 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700 ease-out group-hover:opacity-80"
                      style={{
                        width: `${pct}%`,
                        background: `linear-gradient(90deg, ${color}, ${color}dd)`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Activity Summary (Last 30 days) ─────────────────────────── */}
      {activity_30d && activity_30d.length > 0 && (
        <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-semibold text-white">Activity – Last 30 Days</h2>
              <p className="text-xs text-slate-500 mt-0.5">Sessions and messages per day</p>
            </div>
            <span className="text-2xl">📅</span>
          </div>

          {/* Simple CSS bar chart */}
          <div className="flex items-end gap-1 h-32 overflow-x-auto pb-2">
            {activity_30d.slice(-30).map((day, i) => {
              const total = day.sessions + day.messages;
              const height = maxActivity > 0 ? (total / maxActivity) * 100 : 0;
              return (
                <div
                  key={day.date}
                  className="group relative flex-1 min-w-[8px] flex flex-col items-center justify-end"
                >
                  <div
                    className="w-full rounded-t-sm bg-gradient-to-t from-blue-500 to-violet-500 opacity-70 hover:opacity-100 transition-opacity cursor-pointer"
                    style={{ height: `${Math.max(height, 4)}%` }}
                    title={`${day.date}: ${day.sessions} sessions, ${day.messages} msgs`}
                  />
                  {/* Tooltip on hover */}
                  <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-slate-700 text-white text-xs px-2 py-1 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                    {day.sessions}s · {day.messages}m
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-2 text-xs text-slate-600">
            <span>30 days ago</span>
            <span>Today</span>
          </div>

          {/* Summary stats row */}
          <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-white/5">
            <div className="text-center">
              <p className="text-xl font-bold text-white font-mono">
                {activity_30d.reduce((sum, d) => sum + d.sessions, 0)}
              </p>
              <p className="text-xs text-slate-500">Total Sessions</p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-white font-mono">
                {activity_30d.reduce((sum, d) => sum + d.messages, 0)}
              </p>
              <p className="text-xs text-slate-500">Total Messages</p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-white font-mono">
                {Math.round(
                  activity_30d.reduce((sum, d) => sum + d.sessions, 0) / activity_30d.length
                )}
              </p>
              <p className="text-xs text-slate-500">Avg/Day</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Quota & School Info ─────────────────────────────────────── */}
      {workspace && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-5">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-2xl">🏫</span>
              <div>
                <p className="text-white font-semibold">{workspace.school_name}</p>
                <p className="text-xs text-slate-500">{workspace.school_code} · {workspace.plan_type}</p>
              </div>
            </div>
            <div className="mt-3">
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-slate-400">Monthly quota used</span>
                <span className={`font-semibold font-mono ${
                  workspace.quota_used_pct > 80 ? "text-red-400" : workspace.quota_used_pct > 60 ? "text-amber-400" : "text-emerald-400"
                }`}>
                  {workspace.quota_used_pct}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-700">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(workspace.quota_used_pct, 100)}%`,
                    background: workspace.quota_used_pct > 80
                      ? "#EF4444"
                      : workspace.quota_used_pct > 60
                        ? "#F59E0B"
                        : "#10B981",
                  }}
                />
              </div>
            </div>
          </div>
          <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-5">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-2xl">👨‍🏫</span>
              <div>
                <p className="text-white font-semibold">Team Overview</p>
                <p className="text-xs text-slate-500">Teachers and content</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-2">
              <div className="bg-slate-700/30 rounded-xl p-3 text-center">
                <p className="text-2xl font-bold text-blue-400 font-mono">{team?.teacher_count || 0}</p>
                <p className="text-xs text-slate-500 mt-1">Teachers</p>
              </div>
              <div className="bg-slate-700/30 rounded-xl p-3 text-center">
                <p className="text-2xl font-bold text-violet-400 font-mono">{team?.content_pieces || 0}</p>
                <p className="text-xs text-slate-500 mt-1">Content</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Stat Card Component ───────────────────────────────────────────────────────
function StatCard({
  label, value, sub, color, emoji, delay,
}: {
  label: string; value: string; sub: string; color: string; emoji: string; delay: number;
}) {
  return (
    <div className={`bg-slate-800/50 rounded-2xl border border-white/5 p-5 fade-up fade-up-delay-${delay}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400">{label}</p>
          <p className="text-3xl font-bold mt-1.5 font-mono" style={{ color }}>
            {value}
          </p>
          <p className="text-xs text-slate-500 mt-1">{sub}</p>
        </div>
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
          style={{ background: `${color}15` }}
        >
          {emoji}
        </div>
      </div>
    </div>
  );
}

// ── Quick Action Component ────────────────────────────────────────────────────
function QuickAction({
  emoji, label, color, href,
}: {
  emoji: string; label: string; color: string; href: string;
}) {
  return (
    <a
      href={href}
      className="bg-slate-800/50 rounded-xl border border-white/5 p-4 flex flex-col items-center gap-2 hover:bg-slate-700/50 hover:border-white/10 transition-all cursor-pointer group"
    >
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center text-xl group-hover:scale-110 transition-transform"
        style={{ background: `${color}15` }}
      >
        {emoji}
      </div>
      <p className="text-xs font-medium text-slate-300 text-center">{label}</p>
    </a>
  );
}

// ── Loading Skeleton ──────────────────────────────────────────────────────────
function OverviewSkeleton() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-pulse">
      {/* Header skeleton */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-slate-700" />
        <div className="h-7 bg-slate-700 rounded-lg w-64" />
      </div>

      {/* Stats skeleton */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-slate-800/50 rounded-2xl border border-white/5 p-5 h-28">
            <div className="h-3 bg-slate-700 rounded w-20 mb-3" />
            <div className="h-8 bg-slate-700 rounded w-16 mb-2" />
            <div className="h-2.5 bg-slate-700/50 rounded w-24" />
          </div>
        ))}
      </div>

      {/* Quick actions skeleton */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-slate-800/50 rounded-xl border border-white/5 p-4 h-24" />
        ))}
      </div>

      {/* Chart skeleton */}
      <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-6 h-56" />

      {/* Activity skeleton */}
      <div className="bg-slate-800/50 rounded-2xl border border-white/5 p-6 h-48" />
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
        <p className="font-semibold text-white">Failed to load dashboard</p>
        <p className="text-sm text-slate-400 mt-1">Check your connection or try refreshing</p>
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
