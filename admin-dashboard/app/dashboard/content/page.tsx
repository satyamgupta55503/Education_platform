"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { Search, FileText, Filter } from "lucide-react";
import { clsx } from "clsx";
import { adminApi } from "@/lib/api";
import AdminLayout from "@/components/layout/AdminLayout";

const SUBJECTS = ["science", "maths", "hindi", "english", "sst", "gk"];
const SUBJECT_COLORS: Record<string, string> = {
  science: "#10B981", maths: "#8B5CF6", hindi: "#EF4444",
  english: "#3B82F6", sst: "#F59E0B", gk: "#06B6D4",
};
const STATUS_STYLES: Record<string, { bg: string; color: string }> = {
  published: { bg: "#ECFDF5", color: "#059669" },
  draft: { bg: "#F3F4F6", color: "#6B7280" },
  review: { bg: "#FFFBEB", color: "#D97706" },
  archived: { bg: "#FEF2F2", color: "#DC2626" },
};

export default function ContentPage() {
  const [subject, setSubject] = useState<string | undefined>();
  const [grade, setGrade] = useState<number | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ["admin-content", subject, grade],
    queryFn: () => adminApi.listContent({ subject, grade }).then((r) => r.data?.data || r.data),
  });

  const items = data?.items || [];

  return (
    <AdminLayout>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Content</h1>
            <p className="text-sm text-gray-400">
              {items.length} items loaded
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="card p-4 flex flex-wrap gap-3">
          <div className="flex gap-1.5 flex-wrap">
            {[undefined, ...SUBJECTS].map((s) => (
              <button
                key={s ?? "all"}
                onClick={() => setSubject(s)}
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all capitalize",
                  subject === s
                    ? "text-white shadow-sm"
                    : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
                )}
                style={subject === s ? { background: s ? SUBJECT_COLORS[s] : "#374151" } : {}}
              >
                {s ?? "All Subjects"}
              </button>
            ))}
          </div>
          <select
            value={grade ?? ""}
            onChange={(e) => setGrade(e.target.value ? +e.target.value : undefined)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none bg-white"
          >
            <option value="">All Grades</option>
            {[1,2,3,4,5,6,7,8,9,10].map((g) => (
              <option key={g} value={g}>Grade {g}</option>
            ))}
          </select>
        </div>

        {/* Content Table */}
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="th text-left">Title</th>
                  <th className="th text-left hidden sm:table-cell">Subject</th>
                  <th className="th text-left hidden md:table-cell">Grade</th>
                  <th className="th text-left hidden md:table-cell">Type</th>
                  <th className="th text-left">Status</th>
                  <th className="th text-left hidden lg:table-cell">Created</th>
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? [...Array(8)].map((_, i) => (
                      <tr key={i}>
                        <td colSpan={6} className="td">
                          <div className="h-5 skeleton rounded w-full" />
                        </td>
                      </tr>
                    ))
                  : items.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="td text-center py-12">
                          <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                          <p className="text-gray-500 font-medium">No content found</p>
                          <p className="text-xs text-gray-400 mt-1">Try changing filters</p>
                        </td>
                      </tr>
                    )
                  : items.map((item: any) => {
                      const color = SUBJECT_COLORS[item.subject] || "#6B7280";
                      const statusStyle = STATUS_STYLES[item.status] || STATUS_STYLES.draft;
                      return (
                        <tr key={item.content_id} className="hover:bg-gray-50/60 transition-colors">
                          <td className="td">
                            <div className="flex items-center gap-3">
                              <div
                                className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0"
                                style={{ background: color + "18", color }}
                              >
                                {(item.content_type || "?")[0].toUpperCase()}
                              </div>
                              <div className="min-w-0">
                                <p className="font-medium text-gray-900 text-sm truncate max-w-[200px]">
                                  {item.title}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="td hidden sm:table-cell">
                            <span
                              className="badge text-xs capitalize"
                              style={{ background: color + "18", color }}
                            >
                              {item.subject}
                            </span>
                          </td>
                          <td className="td hidden md:table-cell">
                            <span className="badge b-blue text-xs">Cl.{item.grade}</span>
                          </td>
                          <td className="td hidden md:table-cell">
                            <span className="text-xs text-gray-500 capitalize">
                              {item.content_type}
                            </span>
                          </td>
                          <td className="td">
                            <span
                              className="badge text-xs capitalize"
                              style={{ background: statusStyle.bg, color: statusStyle.color }}
                            >
                              {item.status}
                            </span>
                          </td>
                          <td className="td hidden lg:table-cell">
                            <span className="text-xs text-gray-400">
                              {item.created_at
                                ? format(parseISO(item.created_at), "dd MMM yy")
                                : "—"}
                            </span>
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
