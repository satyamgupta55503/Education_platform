"use client";
// app/dashboard/cache/page.tsx
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { Zap, Database, Volume2, Server } from "lucide-react";
import { adminApi } from "@/lib/api";
import AdminLayout from "@/components/layout/AdminLayout";

const SUBJECT_COLORS: Record<string, string> = {
  science: "#10B981", maths: "#8B5CF6", hindi: "#EF4444",
  english: "#3B82F6", sst: "#F59E0B", gk: "#06B6D4",
};

export default function CachePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-cache"],
    queryFn: () => adminApi.getCacheHealth().then((r) => r.data?.data || r.data),
    refetchInterval: 60_000,
  });

  const l2Data = data?.l2_semantic?.by_subject_grade ?? [];
  const audioData = data?.audio_cache?.by_language ?? [];
  const totalAudioKB = audioData.reduce((a, r) => a + r.total_size_kb, 0);

  const chartData = l2Data.map((r) => ({
    label: `${r.subject.slice(0,3).toUpperCase()}${r.grade}`,
    entries: r.entries, hits: r.total_hits,
    color: SUBJECT_COLORS[r.subject] ?? "#94A3B8",
  }));

  return (
    <AdminLayout>
      <div className="space-y-5">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Cache Health</h1>
          <p className="text-sm text-gray-400">3-layer intelligent caching system</p>
        </div>

        {/* Cache architecture overview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 fade">
          {[
            {
              icon: Zap, label: "L1 Redis (Exact)",
              value: data?.l1_redis?.key_count?.toLocaleString() ?? "—",
              sub: "SHA-256 hash keys", color: "#10B981", bg: "#ECFDF5",
              detail: "< 1ms hit time · 8-12% hit rate · 7-day TTL",
            },
            {
              icon: Database, label: "L2 Semantic Cache",
              value: l2Data.reduce((a, r) => a + r.entries, 0).toLocaleString(),
              sub: "pgvector cosine similarity", color: "#3B82F6", bg: "#EFF6FF",
              detail: "~15ms hit · 35-45% hit rate · 30-day TTL",
            },
            {
              icon: Volume2, label: "Audio Cache",
              value: audioData.reduce((a, r) => a + r.entries, 0).toString(),
              sub: `${(totalAudioKB / 1024).toFixed(1)} MB stored`, color: "#8B5CF6", bg: "#F5F3FF",
              detail: "TTS pre-generated · 90-day TTL · CDN-served",
            },
          ].map(({ icon: Icon, label, value, sub, color, bg, detail }) => (
            <div key={label} className="card p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <div className="p-2 rounded-lg" style={{ background: bg }}>
                      <Icon size={15} style={{ color }} />
                    </div>
                    <span className="text-xs font-semibold text-gray-500">{label}</span>
                  </div>
                  <p className="text-2xl font-bold mono" style={{ color }}>{value}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{sub}</p>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-400">{detail}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Redis info */}
        {data?.l1_redis && (
          <div className="card p-4 flex items-center gap-4 fade">
            <div className="p-3 rounded-xl bg-gray-100">
              <Server size={18} className="text-gray-600" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-gray-800 text-sm">Redis Memory Usage</p>
              <div className="flex items-center gap-3 mt-1">
                <div className="flex-1 prog-bar">
                  <div className="prog-fill bg-emerald-500"
                    style={{
                      width: `${Math.min(
                        ((data.l1_redis as any)?.used_memory_mb ?? 0) / 512 * 100, 100
                      )}%`,
                    }} />
                </div>
                <span className="mono text-xs font-semibold text-gray-600">
                  {(data.l1_redis as any)?.used_memory_mb ?? 0}MB / 512MB
                </span>
              </div>
            </div>
          </div>
        )}

        {/* L2 by subject chart */}
        {chartData.length > 0 && (
          <div className="card p-5 fade">
            <h2 className="font-semibold text-gray-800 mb-4">
              L2 Semantic Cache — Hits by Subject × Grade
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ left: -20, right: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#9CA3AF" }}
                  tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#9CA3AF" }}
                  tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 10, border: "none",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.08)" }} />
                <Bar dataKey="hits" name="Cache Hits" radius={[4,4,0,0]}>
                  {chartData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* L2 detail table */}
        {l2Data.length > 0 && (
          <div className="card overflow-hidden fade">
            <div className="p-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Semantic Cache Detail</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="th text-left">Subject</th>
                    <th className="th text-left">Grade</th>
                    <th className="th text-right">Entries</th>
                    <th className="th text-right">Total Hits</th>
                    <th className="th text-right">Avg Hits/Entry</th>
                    <th className="th text-left hidden md:table-cell">Engagement</th>
                  </tr>
                </thead>
                <tbody>
                  {l2Data.map((r, i) => {
                    const color = SUBJECT_COLORS[r.subject] ?? "#94A3B8";
                    const maxHits = Math.max(...l2Data.map((x) => x.total_hits), 1);
                    return (
                      <tr key={i} className="hover:bg-gray-50/60 transition-colors">
                        <td className="td">
                          <div className="flex items-center gap-2">
                            <div className="w-2.5 h-2.5 rounded-full"
                              style={{ background: color }} />
                            <span className="capitalize font-medium">{r.subject}</span>
                          </div>
                        </td>
                        <td className="td">
                          <span className="badge b-blue">Class {r.grade}</span>
                        </td>
                        <td className="td text-right mono font-medium">{r.entries}</td>
                        <td className="td text-right mono font-bold"
                          style={{ color }}>{r.total_hits.toLocaleString()}</td>
                        <td className="td text-right mono text-gray-500">
                          {r.avg_hits_per_entry.toFixed(1)}
                        </td>
                        <td className="td hidden md:table-cell">
                          <div className="w-24 prog-bar">
                            <div className="prog-fill"
                              style={{
                                width: `${(r.total_hits / maxHits) * 100}%`,
                                background: color,
                              }} />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Thresholds reference */}
        <div className="card p-5 fade">
          <h3 className="font-semibold text-gray-800 mb-3 text-sm">
            Semantic Cache Thresholds (cosine similarity)
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { subject: "Maths",   threshold: "0.96", reason: "Exact formulas" },
              { subject: "Science", threshold: "0.92", reason: "Core concepts" },
              { subject: "English", threshold: "0.91", reason: "Grammar rules" },
              { subject: "SST",     threshold: "0.90", reason: "Facts & dates" },
              { subject: "Hindi",   threshold: "0.89", reason: "Language variety" },
              { subject: "GK",      threshold: "0.87", reason: "Broad topics" },
            ].map((t) => (
              <div key={t.subject} className="p-3 rounded-xl bg-gray-50 border border-gray-100 text-center">
                <p className="text-xs font-semibold text-gray-700">{t.subject}</p>
                <p className="mono font-bold text-lg mt-1 text-blue-600">{t.threshold}</p>
                <p className="text-xs text-gray-400 mt-0.5">{t.reason}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
