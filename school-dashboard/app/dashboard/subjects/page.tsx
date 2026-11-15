"use client";
// app/dashboard/subjects/page.tsx
import { useQuery } from "@tanstack/react-query";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";
import { schoolApi, SubjectStat } from "@/lib/api";
// Layout is provided by app/dashboard/layout.tsx
import { BookOpen, Video, FileText, Users, MessageSquare } from "lucide-react";

const SUBJECT_COLORS: Record<string, string> = {
  science: "#10B981", maths: "#8B5CF6", hindi: "#EF4444",
  english: "#3B82F6", sst: "#F59E0B", gk: "#06B6D4",
};
const SUBJECT_ICONS: Record<string, string> = {
  science: "🔬", maths: "📐", hindi: "🔤", english: "📖", sst: "🌍", gk: "🌟",
};

function MasteryRing({ pct, color }: { pct: number; color: string }) {
  const r = 28; const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  return (
    <svg width="72" height="72" className="shrink-0">
      <circle cx="36" cy="36" r={r} fill="none" stroke="#F1F5F9" strokeWidth="5" />
      <circle cx="36" cy="36" r={r} fill="none" stroke={color} strokeWidth="5"
        strokeDasharray={`${dash} ${circ}`} strokeDashoffset={circ * 0.25}
        strokeLinecap="round" style={{ transition: "stroke-dasharray 0.6s ease" }} />
      <text x="36" y="40" textAnchor="middle"
        style={{ fontFamily: "'DM Mono', monospace", fontSize: 12, fontWeight: 700, fill: color }}>
        {pct.toFixed(0)}%
      </text>
    </svg>
  );
}

export default function SubjectsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["school-subjects"],
    queryFn: () => schoolApi.getSubjects().then((r) => r.data?.data || r.data),
  });

  const subjects = data?.subjects || [];
  const radarData = subjects.map((s: any) => ({
    subject: s.subject.charAt(0).toUpperCase() + s.subject.slice(1),
    mastery: s.avg_mastery_pct || 0,
    content: Math.min(((s.total_chunks || 0) / 100) * 100, 100),
  }));

  return (
    <>
      <div className="space-y-5">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Subject Analytics</h1>
          <p className="text-sm text-gray-500 mt-0.5">Content coverage and student mastery per subject</p>
        </div>

        {/* Radar + cards grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Radar */}
          <div className="card p-5">
            <h2 className="font-semibold text-gray-800 mb-4 text-sm">Overall Mastery Radar</h2>
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#F1F5F9" />
                <PolarAngleAxis dataKey="subject"
                  tick={{ fontSize: 11, fill: "#94A3B8", fontFamily: "'DM Sans'" }} />
                <Radar name="Mastery" dataKey="mastery" stroke="#3B82F6"
                  fill="#3B82F6" fillOpacity={0.15} strokeWidth={2} />
                <Radar name="Content" dataKey="content" stroke="#10B981"
                  fill="#10B981" fillOpacity={0.08} strokeWidth={1.5} strokeDasharray="4 3" />
              </RadarChart>
            </ResponsiveContainer>
            <div className="flex gap-4 justify-center mt-2 text-xs text-gray-400">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-0.5 bg-blue-500 rounded" />
                <span>Mastery %</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-0.5 bg-emerald-500 rounded" style={{ borderStyle: "dashed" }} />
                <span>Content coverage</span>
              </div>
            </div>
          </div>

          {/* Subject cards */}
          <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {isLoading
              ? [...Array(6)].map((_, i) => (
                  <div key={i} className="card p-4 h-36 skeleton rounded-2xl" />
                ))
              : data?.subjects.map((s: SubjectStat) => {
                  const color  = SUBJECT_COLORS[s.subject] ?? "#94A3B8";
                  const icon   = SUBJECT_ICONS[s.subject] ?? "📚";
                  const pct    = s.avg_mastery_pct ?? 0;
                  return (
                    <div key={s.subject}
                      className="card p-4 fade-up"
                      style={{ borderLeft: `4px solid ${color}` }}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xl">{icon}</span>
                            <h3 className="font-bold text-gray-800 capitalize text-sm">
                              {s.subject}
                            </h3>
                          </div>
                          <div className="grid grid-cols-2 gap-y-2 mt-3">
                            <StatPill icon={<FileText size={11} />}
                              label="PDFs" value={s.pdfs} />
                            <StatPill icon={<Video size={11} />}
                              label="Videos" value={s.videos} />
                            <StatPill icon={<Users size={11} />}
                              label="Students" value={s.unique_students} />
                            <StatPill icon={<MessageSquare size={11} />}
                              label="Messages" value={s.total_messages} />
                          </div>
                        </div>
                        <MasteryRing pct={pct} color={color} />
                      </div>
                      {/* Mini bar */}
                      <div className="mt-3">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-400">Avg mastery</span>
                          <span className="font-semibold num" style={{ color }}>
                            {pct.toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-1.5 rounded-full bg-gray-100">
                          <div className="h-full rounded-full transition-all"
                            style={{ width: `${pct}%`, background: color }} />
                        </div>
                      </div>
                    </div>
                  );
                })}
          </div>
        </div>
      </div>
    </>
  );
}

function StatPill({
  icon, label, value,
}: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-500">
      <span className="text-gray-400">{icon}</span>
      <span>{label}:</span>
      <span className="font-semibold text-gray-700 num">{value}</span>
    </div>
  );
}
