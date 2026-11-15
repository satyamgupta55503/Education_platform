"use client";
// app/dashboard/students/page.tsx
import { useState, useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Search, SlidersHorizontal, ChevronLeft, ChevronRight,
  TrendingDown, Trophy, Flame, Star, Copy, Check,
} from "lucide-react";
import { formatDistanceToNow, parseISO } from "date-fns";
import { clsx } from "clsx";
import { schoolApi, Student } from "@/lib/api";
// Layout is provided by app/dashboard/layout.tsx

const GRADES = [1,2,3,4,5,6,7,8,9,10];
const SORT_OPTIONS = [
  { value: "brain_coins",  label: "Brain Coins" },
  { value: "streak_days", label: "Streak" },
  { value: "last_active", label: "Last Active" },
  { value: "created_at",  label: "Joined" },
];
const TIER_STYLES: Record<string, string> = {
  genius: "badge-amber", smart: "badge-blue", free: "badge-gray",
};

function MasteryBar({ pct }: { pct: number }) {
  const color = pct >= 70 ? "#10B981" : pct >= 40 ? "#F59E0B" : "#EF4444";
  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className="flex-1 h-1.5 rounded-full bg-gray-100">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(pct, 100)}%`, background: color }}
        />
      </div>
      <span className="text-xs font-semibold num w-9 text-right" style={{ color }}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

function CopyId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button onClick={copy}
      className="flex items-center gap-1 group" title="Copy EduCat ID">
      <span className="text-xs num text-gray-400 font-medium group-hover:text-blue-500 transition-colors">
        {id}
      </span>
      {copied
        ? <Check size={11} className="text-emerald-500" />
        : <Copy size={11} className="text-gray-300 group-hover:text-blue-400 transition-colors" />}
    </button>
  );
}

export default function StudentsPage() {
  const [grade, setGrade]     = useState<number | undefined>();
  const [sortBy, setSortBy]   = useState("brain_coins");
  const [order, setOrder]     = useState<"desc" | "asc">("desc");
  const [page, setPage]       = useState(1);
  const [search, setSearch]   = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["school-students", grade, sortBy, order, page],
    queryFn: () =>
      schoolApi.getStudents({ grade, sort_by: sortBy, order, page, limit: 25 })
        .then((r) => r.data?.data || r.data),
    keepPreviousData: true,
  });

  // Client-side name search
  const filtered = useMemo(() => {
    if (!data?.students) return [];
    if (!search.trim()) return data.students;
    const q = search.toLowerCase();
    return data.students.filter(
      (s) =>
        s.display_name?.toLowerCase().includes(q) ||
        s.educat_id?.toLowerCase().includes(q)
    );
  }, [data?.students, search]);

  const handleGrade = useCallback((g?: number) => {
    setGrade(g); setPage(1);
  }, []);

  return (
    <>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Students</h1>
            <p className="text-sm text-gray-500">
              {data?.total ?? "—"} students · Page {data?.page ?? 1} of {data?.pages ?? 1}
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="card p-4 flex flex-wrap gap-3">
          {/* Search */}
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 flex-1 min-w-[180px]">
            <Search size={15} className="text-gray-400 shrink-0" />
            <input
              type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or ID..."
              className="bg-transparent text-sm outline-none w-full placeholder:text-gray-400"
            />
          </div>

          {/* Grade chips */}
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => handleGrade(undefined)}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all",
                !grade ? "bg-blue-600 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              )}
            >All</button>
            {GRADES.map((g) => (
              <button key={g}
                onClick={() => handleGrade(g === grade ? undefined : g)}
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all",
                  grade === g ? "bg-blue-600 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                )}
              >Cl.{g}</button>
            ))}
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <SlidersHorizontal size={14} className="text-gray-400" />
            <select
              value={sortBy} onChange={(e) => setSortBy(e.target.value)}
              className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white outline-none"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <button
              onClick={() => setOrder(order === "desc" ? "asc" : "desc")}
              className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white hover:bg-gray-50"
            >
              {order === "desc" ? "↓" : "↑"}
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="th text-left">#</th>
                  <th className="th text-left">Student</th>
                  <th className="th text-left hidden md:table-cell">EduCat ID</th>
                  <th className="th text-left hidden lg:table-cell">Grade</th>
                  <th className="th text-left hidden sm:table-cell">Tier</th>
                  <th className="th text-left">Mastery</th>
                  <th className="th text-left hidden md:table-cell">🧠 Coins</th>
                  <th className="th text-left hidden lg:table-cell">🔥 Streak</th>
                  <th className="th text-left hidden xl:table-cell">Last Active</th>
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? [...Array(10)].map((_, i) => (
                    <tr key={i} className="table-row">
                      <td colSpan={9} className="td">
                        <div className="h-5 skeleton rounded w-full" />
                      </td>
                    </tr>
                  ))
                  : filtered.map((s: Student, i: number) => (
                    <tr key={s.user_id} className="table-row">
                      <td className="td">
                        <RankBadge rank={(page - 1) * 25 + i + 1} />
                      </td>
                      <td className="td">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
                            style={{ background: tierBg(s.tier), color: tierColor(s.tier) }}>
                            {(s.display_name ?? "?")[0]?.toUpperCase()}
                          </div>
                          <div>
                            <p className="font-semibold text-gray-800 text-sm leading-none">
                              {s.display_name ?? "Student"}
                            </p>
                            <p className="text-xs text-gray-400 mt-0.5">
                              {s.total_sessions} sessions
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="td hidden md:table-cell">
                        <CopyId id={s.educat_id} />
                      </td>
                      <td className="td hidden lg:table-cell">
                        <span className="badge badge-blue">Class {s.grade}</span>
                      </td>
                      <td className="td hidden sm:table-cell">
                        <span className={`badge ${TIER_STYLES[s.tier] ?? "badge-gray"} uppercase`}>
                          {s.tier}
                        </span>
                      </td>
                      <td className="td">
                        <MasteryBar pct={s.overall_mastery_pct ?? 0} />
                      </td>
                      <td className="td hidden md:table-cell">
                        <span className="num font-semibold text-gray-800">{s.brain_coins}</span>
                      </td>
                      <td className="td hidden lg:table-cell">
                        <div className="flex items-center gap-1 text-orange-500">
                          <Flame size={12} />
                          <span className="num font-semibold text-sm">{s.streak_days}d</span>
                        </div>
                      </td>
                      <td className="td hidden xl:table-cell">
                        <span className="text-xs text-gray-400">
                          {s.last_active
                            ? formatDistanceToNow(parseISO(s.last_active), { addSuffix: true })
                            : "Never"}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <p className="text-sm text-gray-500">
                Showing {(page - 1) * 25 + 1}–{Math.min(page * 25, data.total)} of {data.total}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40"
                >
                  <ChevronLeft size={14} />
                </button>
                <span className="text-sm font-medium num">
                  {page} / {data.pages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                  disabled={page === data.pages}
                  className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40"
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) return <span className="text-lg">🥇</span>;
  if (rank === 2) return <span className="text-lg">🥈</span>;
  if (rank === 3) return <span className="text-lg">🥉</span>;
  return <span className="text-sm text-gray-400 num font-medium">{rank}</span>;
}

function tierColor(t: string) {
  return t === "genius" ? "#D97706" : t === "smart" ? "#2563EB" : "#6B7280";
}
function tierBg(t: string) {
  return t === "genius" ? "#FEF3C7" : t === "smart" ? "#DBEAFE" : "#F3F4F6";
}
