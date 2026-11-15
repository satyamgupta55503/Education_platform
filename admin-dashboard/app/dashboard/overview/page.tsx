"use client";
// app/dashboard/overview/page.tsx
import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, PieChart, Pie,
} from "recharts";
import { format, parseISO } from "date-fns";
import {
  Users, Building2, MessageSquare, Zap,
  TrendingUp, Database, Activity, Server,
} from "lucide-react";
import { adminApi, AdminOverview } from "@/lib/api";
import AdminLayout from "@/components/layout/AdminLayout";

const TIER_CFG: Record<string, { color: string; bg: string; emoji: string }> = {
  genius: { color: "#D97706", bg: "#FEF3C7", emoji: "✨" },
  smart:  { color: "#2563EB", bg: "#DBEAFE", emoji: "⚡" },
  free:   { color: "#6B7280", bg: "#F3F4F6", emoji: "🆓" },
};
const PLAN_COLORS: Record<string, string> = {
  classroom: "#3B82F6", institute: "#8B5CF6", campus_plus: "#10B981",
};

export default function AdminOverviewPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-overview"],
    queryFn: () => adminApi.getOverview().then((r) => r.data?.data || r.data),
    refetchInterval: 90_000,
  });

  if (isLoading || !data) return <AdminLayout><PageSkeleton /></AdminLayout>;

  const { users, today, this_week, schools, cache, content } = data;

  const growthData = (users?.growth_30d || []).slice(-14).map((d: any) => ({
    date: d.date ? format(parseISO(d.date), "dd MMM") : "",
    users: d.new_users || 0,
  }));

  const tierPie = Object.entries(users?.by_tier || {}).map(([tier, count]) => ({
    name: tier, value: count as number,
    color: TIER_CFG[tier]?.color ?? "#94A3B8",
  }));

  const planBar = (schools?.by_plan || []).map((p: any) => ({
    plan: (p.plan_type || p.plan || "unknown").replace("_", " "),
    schools: p.count || 0,
    tokens: Math.round((p.total_tokens_used || 0) / 1000),
    color: PLAN_COLORS[p.plan_type || p.plan] ?? "#94A3B8",
  }));

  const cacheRates = cache?.hit_rates_7d || {};
  const cacheTotal = Object.values(cacheRates).reduce((a: number, v: any) => a + (v?.count || 0), 0);

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-gray-900">Platform Overview</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Real-time EduCat AI metrics · refreshes every 90s
          </p>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          <KPICard icon={Users} label="Total Users" value={users.total.toLocaleString()}
            sub={`+${growthData.at(-1)?.users ?? 0} today`}
            color="#2563EB" bg="#EFF6FF" delay="fade-d1" />
          <KPICard icon={Building2} label="Active Schools" value={schools.total}
            sub={`${schools.by_plan.length} plan types`}
            color="#059669" bg="#ECFDF5" delay="fade-d2" />
          <KPICard icon={Activity} label="DAU" value={today.dau.toLocaleString()}
            sub={`${today.sessions} sessions`}
            color="#7C3AED" bg="#F5F3FF" delay="fade-d3" />
          <KPICard icon={Database} label="Content Pieces" value={content.total_pieces.toLocaleString()}
            sub={`${(content.by_subject.reduce((a,b)=>a+b.chunks,0)).toLocaleString()} chunks`}
            color="#D97706" bg="#FFFBEB" delay="fade-d4" />
        </div>

        {/* Today mini row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Messages Today", value: today.messages, icon: "💬" },
            { label: "WAU", value: this_week.wau, icon: "👤" },
            { label: "Tokens Today", value: `${(today.tokens_used/1000).toFixed(1)}K`, icon: "⚡" },
            { label: "Cache Entries", value: cache.semantic_cache_size.toLocaleString(), icon: "🧠" },
          ].map((s) => (
            <div key={s.label} className="card px-4 py-3 flex items-center gap-3">
              <span className="text-xl">{s.icon}</span>
              <div>
                <p className="text-xs text-gray-400 font-medium">{s.label}</p>
                <p className="font-bold text-gray-800 mono">{s.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* User growth */}
          <div className="card p-5 lg:col-span-2 fade fade-d1">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-gray-800">New Users — Last 14 Days</h2>
                <p className="text-xs text-gray-400 mt-0.5">Daily new registrations</p>
              </div>
              <TrendingUp size={15} className="text-gray-300" />
            </div>
            <ResponsiveContainer width="100%" height={190}>
              <LineChart data={growthData} margin={{ left: -20, right: 4 }}>
                <defs>
                  <linearGradient id="gGrow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563EB" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#9CA3AF" }}
                  tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#9CA3AF" }}
                  tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 10, border: "none",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.08)" }} />
                <Line type="monotone" dataKey="users" stroke="#2563EB"
                  strokeWidth={2.5} dot={false} name="New Users" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Tier pie */}
          <div className="card p-5 fade fade-d2">
            <h2 className="font-semibold text-gray-800 mb-1">Users by Tier</h2>
            <p className="text-xs text-gray-400 mb-4">Subscription distribution</p>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={tierPie} cx="50%" cy="50%"
                  innerRadius={40} outerRadius={70}
                  paddingAngle={3} dataKey="value">
                  {tierPie.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "none",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.1)" }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2 mt-3">
              {tierPie.map((t) => {
                const cfg = TIER_CFG[t.name];
                const pct = Math.round((t.value / users.total) * 100);
                return (
                  <div key={t.name} className="flex items-center gap-2">
                    <span>{cfg?.emoji}</span>
                    <span className="text-xs text-gray-500 capitalize flex-1">{t.name}</span>
                    <div className="w-20 prog-bar">
                      <div className="prog-fill" style={{ width: `${pct}%`, background: cfg?.color }} />
                    </div>
                    <span className="mono text-xs font-semibold text-gray-700 w-12 text-right">
                      {t.value.toLocaleString()}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Schools by plan + Cache */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Schools bar */}
          <div className="card p-5 fade fade-d1">
            <h2 className="font-semibold text-gray-800 mb-4">Schools by Plan</h2>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={planBar} margin={{ left: -20, right: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="plan" tick={{ fontSize: 11, fill: "#9CA3AF" }}
                  tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#9CA3AF" }}
                  tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 10, border: "none",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.08)" }} />
                <Bar dataKey="schools" radius={[6,6,0,0]} name="Schools">
                  {planBar.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Cache performance */}
          <div className="card p-5 fade fade-d2">
            <div className="flex items-center gap-2 mb-4">
              <Zap size={15} className="text-amber-500" />
              <h2 className="font-semibold text-gray-800">Cache Performance (7d)</h2>
            </div>
            <div className="space-y-3">
              {Object.entries(cacheRates).map(([key, val]) => {
                const colors: Record<string, string> = {
                  none: "#EF4444", l1: "#10B981", l2: "#3B82F6", l3: "#8B5CF6"
                };
                const labels: Record<string, string> = {
                  none: "Cache Miss", l1: "L1 Redis (Exact)", l2: "L2 Semantic", l3: "L3 Personal"
                };
                return (
                  <div key={key}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-500">{labels[key] ?? key}</span>
                      <span className="mono font-semibold"
                        style={{ color: colors[key] ?? "#6B7280" }}>
                        {val.pct}% ({val.count.toLocaleString()})
                      </span>
                    </div>
                    <div className="prog-bar">
                      <div className="prog-fill"
                        style={{ width: `${val.pct}%`, background: colors[key] ?? "#6B7280" }} />
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 pt-3 border-t border-gray-100 flex justify-between text-xs text-gray-400">
              <span>Redis: {cache.redis_memory.used_memory_mb}MB</span>
              <span>L2 entries: {cache.semantic_cache_size.toLocaleString()}</span>
              <span>Total: {cacheTotal.toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}

function KPICard({ icon: Icon, label, value, sub, color, bg, delay }: {
  icon: any; label: string; value: string | number; sub: string;
  color: string; bg: string; delay: string;
}) {
  return (
    <div className={`card p-5 fade ${delay}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{label}</p>
          <p className="text-2xl font-bold mt-1.5 mono" style={{ color }}>{value}</p>
          <p className="text-xs text-gray-400 mt-1">{sub}</p>
        </div>
        <div className="p-2.5 rounded-xl" style={{ background: bg }}>
          <Icon size={17} style={{ color }} />
        </div>
      </div>
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-7 bg-gray-200 rounded w-52" />
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <div key={i} className="card h-24 skeleton rounded-2xl" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="card h-64 skeleton rounded-2xl lg:col-span-2" />
        <div className="card h-64 skeleton rounded-2xl" />
      </div>
    </div>
  );
}
