"use client";
// app/dashboard/users/page.tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import toast from "react-hot-toast";
import { Search, Users, Flame } from "lucide-react";
import { clsx } from "clsx";
import { adminApi, User } from "@/lib/api";
import AdminLayout from "@/components/layout/AdminLayout";

const TIERS  = ["free", "smart", "genius"];
const GRADES = [1,2,3,4,5,6,7,8,9,10];
const TIER_STYLES: Record<string, { bg: string; color: string; emoji: string }> = {
  free:   { bg: "#F3F4F6", color: "#6B7280", emoji: "🆓" },
  smart:  { bg: "#DBEAFE", color: "#2563EB", emoji: "⚡" },
  genius: { bg: "#FEF3C7", color: "#D97706", emoji: "✨" },
};

export default function UsersPage() {
  const qc            = useQueryClient();
  const [tier, setTier]   = useState<string | undefined>();
  const [grade, setGrade] = useState<number | undefined>();
  const [search, setSearch] = useState("");
  const [changingId, setChangingId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", tier, grade],
    queryFn: () => adminApi.listUsers({ tier, grade }).then((r) => r.data?.data || r.data),
  });

  const changeTier = useMutation({
    mutationFn: ({ userId, newTier }: { userId: string; newTier: string }) =>
      adminApi.updateUserTier(userId, newTier),
    onSuccess: (_, { newTier }) => {
      toast.success(`Tier updated to ${newTier}!`);
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setChangingId(null);
    },
    onError: () => {
      toast.error("Failed to update tier");
      setChangingId(null);
    },
  });

  const filtered = (data?.users || []).filter((u) =>
    !search || u.user_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AdminLayout>
      <div className="space-y-5">
        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-gray-900">Users</h1>
          <p className="text-sm text-gray-400">{(data?.users || []).length || "—"} students loaded</p>
        </div>

        {/* Stats row */}
        {data && (
          <div className="grid grid-cols-3 gap-4 fade">
            {TIERS.map((t) => {
              const count = (data.users || []).filter((u) => u.tier === t).length;
              const cfg = TIER_STYLES[t];
              return (
                <div key={t} className="card p-4 text-center cursor-pointer hover:shadow-md transition-all"
                  onClick={() => setTier(t === tier ? undefined : t)}>
                  <p className="text-2xl">{cfg.emoji}</p>
                  <p className="text-2xl font-bold mono mt-1" style={{ color: cfg.color }}>
                    {count}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5 capitalize">{t}</p>
                </div>
              );
            })}
          </div>
        )}

        {/* Filters */}
        <div className="card p-4 flex flex-wrap gap-3">
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 flex-1 min-w-[160px]">
            <Search size={14} className="text-gray-400 shrink-0" />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by user ID..."
              className="bg-transparent text-sm outline-none w-full placeholder:text-gray-400" />
          </div>

          {/* Tier */}
          <div className="flex gap-1.5 flex-wrap">
            {[undefined, ...TIERS].map((t) => {
              const cfg = t ? TIER_STYLES[t] : null;
              return (
                <button key={t ?? "all"}
                  onClick={() => setTier(t)}
                  className={clsx("px-3 py-1.5 rounded-lg text-xs font-semibold transition-all capitalize",
                    tier === t
                      ? "text-white shadow-sm"
                      : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50")}
                  style={tier === t ? { background: cfg?.color ?? "#374151" } : {}}>
                  {t ? `${cfg?.emoji} ${t}` : "All Tiers"}
                </button>
              );
            })}
          </div>

          {/* Grade */}
          <select value={grade ?? ""} onChange={(e) => setGrade(e.target.value ? +e.target.value : undefined)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none bg-white">
            <option value="">All Classes</option>
            {GRADES.map((g) => <option key={g} value={g}>Class {g}</option>)}
          </select>
        </div>

        {/* Table */}
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="th text-left">User ID</th>
                  <th className="th text-left hidden sm:table-cell">Grade</th>
                  <th className="th text-left hidden md:table-cell">Language</th>
                  <th className="th text-left">Tier</th>
                  <th className="th text-left hidden md:table-cell">🧠 Coins</th>
                  <th className="th text-left hidden lg:table-cell">🔥 Streak</th>
                  <th className="th text-left hidden lg:table-cell">Quota Left</th>
                  <th className="th text-left hidden xl:table-cell">Joined</th>
                  <th className="th text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? [...Array(10)].map((_, i) => (
                      <tr key={i}><td colSpan={9} className="td">
                        <div className="h-4 skeleton rounded w-full" />
                      </td></tr>
                    ))
                  : filtered.map((u: User) => {
                      const cfg = TIER_STYLES[u.tier];
                      return (
                        <tr key={u.user_id} className="hover:bg-gray-50/60 transition-colors">
                          <td className="td">
                            <span className="mono text-xs text-gray-500">
                              {u.user_id.substring(0, 8)}...
                            </span>
                          </td>
                          <td className="td hidden sm:table-cell">
                            <span className="badge b-blue">Cl.{u.grade}</span>
                          </td>
                          <td className="td hidden md:table-cell">
                            <span className="text-sm">{u.language === "hi" ? "🇮🇳 Hindi" : "🇬🇧 English"}</span>
                          </td>
                          <td className="td">
                            <span className="badge capitalize text-xs"
                              style={{ background: cfg.bg, color: cfg.color }}>
                              {cfg.emoji} {u.tier}
                            </span>
                          </td>
                          <td className="td hidden md:table-cell">
                            <span className="mono font-medium">{u.brain_coins}</span>
                          </td>
                          <td className="td hidden lg:table-cell">
                            <div className="flex items-center gap-1 text-orange-500">
                              <Flame size={11} />
                              <span className="mono text-sm font-semibold">{u.streak_days}d</span>
                            </div>
                          </td>
                          <td className="td hidden lg:table-cell">
                            <span className="mono font-medium text-gray-700">
                              {u.tokens_remaining_monthly}
                            </span>
                          </td>
                          <td className="td hidden xl:table-cell">
                            <span className="text-xs text-gray-400">
                              {u.created_at ? format(parseISO(u.created_at), "dd MMM yy") : "—"}
                            </span>
                          </td>
                          <td className="td">
                            {changingId === u.user_id ? (
                              <select
                                defaultValue={u.tier}
                                autoFocus
                                onBlur={() => setChangingId(null)}
                                onChange={(e) => {
                                  if (e.target.value !== u.tier) {
                                    changeTier.mutate({ userId: u.user_id, newTier: e.target.value });
                                  } else {
                                    setChangingId(null);
                                  }
                                }}
                                className="text-xs border border-blue-300 rounded-lg px-2 py-1 outline-none bg-white focus:ring-2 focus:ring-blue-100">
                                {TIERS.map((t) => (
                                  <option key={t} value={t}>{TIER_STYLES[t].emoji} {t}</option>
                                ))}
                              </select>
                            ) : (
                              <button
                                onClick={() => setChangingId(u.user_id)}
                                className="text-xs text-blue-600 hover:text-blue-800 font-medium transition-colors hover:underline">
                                Change tier
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
