"use client";
// app/dashboard/revenue/page.tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, LineChart, Line,
} from "recharts";
import { format, parseISO } from "date-fns";
import { DollarSign, TrendingUp, Users, CreditCard } from "lucide-react";
import { adminApi, RevenueRow } from "@/lib/api";
import AdminLayout from "@/components/layout/AdminLayout";

const TIER_COLORS: Record<string, string> = {
  genius: "#D97706", smart: "#2563EB", free: "#6B7280",
};

export default function RevenuePage() {
  const [months, setMonths] = useState(6);
  const { data, isLoading } = useQuery({
    queryKey: ["admin-revenue", months],
    queryFn: () => adminApi.getRevenue(months).then((r) => r.data?.data || r.data),
  });

  // Aggregate by month for chart
  const byMonth = (data?.monthly_revenue || []).reduce((acc, r) => {
    const m = r.month.substring(0, 7);
    if (!acc[m]) acc[m] = { month: format(parseISO(r.month), "MMM yy"), total: 0, subs: 0 };
    acc[m].total += r.revenue_inr;
    acc[m].subs  += r.subscriptions;
    return acc;
  }, {} as Record<string, any>);

  const chartData = Object.values(byMonth ?? {});

  return (
    <AdminLayout>
      <div className="space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Revenue</h1>
            <p className="text-sm text-gray-400">Subscription revenue by plan and month</p>
          </div>
          <select value={months} onChange={(e) => setMonths(+e.target.value)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none bg-white">
            {[3, 6, 12].map((m) => <option key={m} value={m}>{m} months</option>)}
          </select>
        </div>

        {/* Summary KPIs */}
        {data && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 fade">
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-1">
                <DollarSign size={16} className="text-emerald-500" />
                <span className="text-xs text-gray-500">Total Revenue</span>
              </div>
              <p className="text-2xl font-bold mono text-gray-900">
                ₹{(data.total_active?.total_inr || 0).toLocaleString()}
              </p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-1">
                <Users size={16} className="text-blue-500" />
                <span className="text-xs text-gray-500">Active Subs</span>
              </div>
              <p className="text-2xl font-bold mono text-gray-900">
                {(data.total_active?.total_subs || 0).toLocaleString()}
              </p>
            </div>
            {["smart", "genius"].map((tier) => {
              const rows = (data.monthly_revenue || []).filter((r) => r.tier === tier);
              const total = rows.reduce((a, r) => a + r.revenue_inr, 0);
              const subs  = rows.reduce((a, r) => a + r.subscriptions, 0);
              return (
                <div key={tier} className="card p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <CreditCard size={16} style={{ color: TIER_COLORS[tier] }} />
                    <span className="text-xs text-gray-500 capitalize">{tier}</span>
                  </div>
                  <p className="text-2xl font-bold mono" style={{ color: TIER_COLORS[tier] }}>
                    ₹{total.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">{subs} subs</p>
                </div>
              );
            })}
          </div>
        )}

        {/* Monthly chart */}
        {chartData.length > 0 && (
          <div className="card p-5">
            <h2 className="font-semibold text-gray-800 mb-4">Monthly Revenue (₹)</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ left: -10, right: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#9CA3AF" }}
                  tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#9CA3AF" }}
                  tickLine={false} axisLine={false}
                  tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
                <Tooltip
                  formatter={(v: number) => [`₹${v.toLocaleString()}`, "Revenue"]}
                  contentStyle={{ fontSize: 12, borderRadius: 10, border: "none",
                    boxShadow: "0 4px 20px rgba(0,0,0,0.08)" }} />
                <Bar dataKey="total" radius={[6,6,0,0]} fill="#2563EB" name="Revenue" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Breakdown table */}
        {data && (
          <div className="card overflow-hidden">
            <div className="p-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Monthly Breakdown</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="th text-left">Month</th>
                    <th className="th text-left">Tier</th>
                    <th className="th text-right">Subscribers</th>
                    <th className="th text-right">Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.monthly_revenue || []).map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50/60 transition-colors">
                      <td className="td mono text-xs">{r.month.substring(0, 7)}</td>
                      <td className="td">
                        <span className="badge capitalize text-xs"
                          style={{
                            background: (TIER_COLORS[r.tier] ?? "#6B7280") + "18",
                            color: TIER_COLORS[r.tier] ?? "#6B7280",
                          }}>
                          {r.tier === "genius" ? "✨" : r.tier === "smart" ? "⚡" : "🆓"} {r.tier}
                        </span>
                      </td>
                      <td className="td text-right mono font-medium">{r.subscriptions}</td>
                      <td className="td text-right mono font-bold text-emerald-600">
                        ₹{r.revenue_inr.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
