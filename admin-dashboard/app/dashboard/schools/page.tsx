"use client";
// app/dashboard/schools/page.tsx
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import toast from "react-hot-toast";
import {
  Search, Plus, ChevronLeft, ChevronRight,
  Building2, AlertTriangle, X, CheckCircle2,
} from "lucide-react";
import { clsx } from "clsx";
import { adminApi, School, WorkspaceCreate } from "@/lib/api";
import AdminLayout from "@/components/layout/AdminLayout";

const PLAN_COLORS: Record<string, string> = {
  classroom: "#3B82F6", institute: "#8B5CF6", campus_plus: "#10B981",
};
const PLAN_OPTS = ["classroom", "institute", "campus_plus"];

function QuotaBar({ pct }: { pct: number }) {
  const color = pct > 80 ? "#EF4444" : pct > 60 ? "#D97706" : "#059669";
  return (
    <div className="flex items-center gap-2 min-w-[90px]">
      <div className="flex-1 h-1.5 rounded-full bg-gray-100">
        <div className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(pct, 100)}%`, background: color }} />
      </div>
      <span className="mono text-xs font-semibold w-9 text-right" style={{ color }}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

function CreateModal({
  onClose, onCreated,
}: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState<WorkspaceCreate>({
    school_name: "", school_code: "", plan_type: "classroom",
    max_teachers: 5, monthly_quota: 10000,
    contact_email: "", state: "", city: "",
  });

  const mutation = useMutation({
    mutationFn: () => adminApi.createWorkspace(form),
    onSuccess: () => {
      toast.success("School workspace created!");
      onCreated(); onClose();
    },
    onError: () => toast.error("Failed to create workspace. Check all fields."),
  });

  const set = (k: keyof WorkspaceCreate) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose} />
      <div className="relative z-10 bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div>
            <h2 className="font-bold text-gray-900">Add School Workspace</h2>
            <p className="text-xs text-gray-400 mt-0.5">Set up a new school on EduCat AI</p>
          </div>
          <button onClick={onClose}
            className="p-2 rounded-xl hover:bg-gray-100 transition-colors">
            <X size={16} className="text-gray-500" />
          </button>
        </div>

        {/* Form */}
        <div className="p-5 space-y-4">
          <Field label="School Name" required>
            <input value={form.school_name} onChange={set("school_name")}
              placeholder="Delhi Public School"
              className="input-field" />
          </Field>
          <Field label="School Code" required hint="Unique 3–20 char code">
            <input value={form.school_code} onChange={set("school_code")}
              placeholder="DPS-DEL-001"
              className="input-field font-mono" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="State">
              <input value={form.state} onChange={set("state")}
                placeholder="Delhi" className="input-field" />
            </Field>
            <Field label="City">
              <input value={form.city} onChange={set("city")}
                placeholder="New Delhi" className="input-field" />
            </Field>
          </div>
          <Field label="Contact Email" required>
            <input type="email" value={form.contact_email} onChange={set("contact_email")}
              placeholder="principal@school.edu" className="input-field" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Plan Type">
              <select value={form.plan_type}
                onChange={(e) => setForm((f) => ({ ...f, plan_type: e.target.value }))}
                className="input-field">
                {PLAN_OPTS.map((p) => (
                  <option key={p} value={p}>
                    {p.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Max Teachers">
              <input type="number" value={form.max_teachers} min={1} max={500}
                onChange={(e) => setForm((f) => ({ ...f, max_teachers: +e.target.value }))}
                className="input-field" />
            </Field>
          </div>
          <Field label="Monthly Quota (questions)">
            <input type="number" value={form.monthly_quota} min={100}
              onChange={(e) => setForm((f) => ({ ...f, monthly_quota: +e.target.value }))}
              className="input-field" />
          </Field>
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-5 border-t border-gray-100">
          <button onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !form.school_name || !form.school_code}
            className="flex-1 py-2.5 rounded-xl text-white text-sm font-semibold transition-all disabled:opacity-50"
            style={{ background: "linear-gradient(135deg, #2563EB, #1D4ED8)" }}>
            {mutation.isPending ? "Creating..." : "Create School"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label, children, required, hint,
}: { label: string; children: React.ReactNode; required?: boolean; hint?: string }) {
  return (
    <div>
      <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1.5 block">
        {label}
        {required && <span className="text-red-400">*</span>}
        {hint && <span className="font-normal normal-case text-gray-400">({hint})</span>}
      </label>
      {children}
    </div>
  );
}

export default function SchoolsPage() {
  const qc = useQueryClient();
  const [page, setPage]         = useState(1);
  const [planFilter, setPlan]   = useState<string | undefined>();
  const [search, setSearch]     = useState("");
  const [showCreate, setCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-schools", planFilter, page],
    queryFn: () =>
      adminApi.getSchools({ plan_type: planFilter, page }).then((r) => r.data?.data || r.data),
    keepPreviousData: true,
  });

  const schools = data?.schools || [];
  const filtered = schools.filter((s: any) =>
    !search ||
    (s.school_name || "").toLowerCase().includes(search.toLowerCase()) ||
    (s.school_code || "").toLowerCase().includes(search.toLowerCase()) ||
    (s.city || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AdminLayout>
      {showCreate && (
        <CreateModal
          onClose={() => setCreate(false)}
          onCreated={() => qc.invalidateQueries({ queryKey: ["admin-schools"] })}
        />
      )}

      <div className="space-y-5">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Schools</h1>
            <p className="text-sm text-gray-400">
              {data?.total ?? "—"} workspaces registered
            </p>
          </div>
          <button onClick={() => setCreate(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-white text-sm font-semibold transition-all hover:opacity-90"
            style={{ background: "linear-gradient(135deg, #2563EB, #1D4ED8)" }}>
            <Plus size={15} />
            Add School
          </button>
        </div>

        {/* Filters */}
        <div className="card p-4 flex flex-wrap gap-3">
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 flex-1 min-w-[200px]">
            <Search size={14} className="text-gray-400 shrink-0" />
            <input
              value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search schools, codes, cities..."
              className="bg-transparent text-sm outline-none w-full placeholder:text-gray-400"
            />
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {[undefined, ...PLAN_OPTS].map((p) => (
              <button key={p ?? "all"}
                onClick={() => { setPlan(p); setPage(1); }}
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all capitalize",
                  planFilter === p
                    ? "text-white shadow-sm"
                    : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
                )}
                style={planFilter === p
                  ? { background: p ? PLAN_COLORS[p] : "#374151" }
                  : {}}>
                {p ? p.replace("_", " ") : "All Plans"}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="th text-left">School</th>
                  <th className="th text-left hidden md:table-cell">Code</th>
                  <th className="th text-left hidden lg:table-cell">Location</th>
                  <th className="th text-left hidden sm:table-cell">Plan</th>
                  <th className="th text-left">Quota</th>
                  <th className="th text-left hidden md:table-cell">Teachers</th>
                  <th className="th text-left hidden lg:table-cell">Content</th>
                  <th className="th text-left hidden xl:table-cell">Joined</th>
                  <th className="th text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {isLoading
                  ? [...Array(8)].map((_, i) => (
                      <tr key={i}>
                        <td colSpan={9} className="td">
                          <div className="h-5 skeleton rounded w-full" />
                        </td>
                      </tr>
                    ))
                  : filtered.map((s: any) => {
                      const planType = s.plan_type || s.subscription_plan || "classroom";
                      const quotaPct = s.quota_used_pct ?? (s.monthly_query_quota ? Math.round((s.queries_used || 0) / s.monthly_query_quota * 100) : 0);
                      return (
                      <tr key={s.workspace_id} className="hover:bg-gray-50/60 transition-colors">
                        <td className="td">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold shrink-0"
                              style={{
                                background: (PLAN_COLORS[planType] ?? "#6B7280") + "20",
                                color: PLAN_COLORS[planType] ?? "#6B7280",
                              }}>
                              {(s.school_name || "?")[0]?.toUpperCase()}
                            </div>
                            <div>
                              <p className="font-semibold text-gray-900 text-sm">{s.school_name}</p>
                              <p className="text-xs text-gray-400 mt-0.5">{s.contact_email || s.admin_email || ""}</p>
                            </div>
                          </div>
                        </td>
                        <td className="td hidden md:table-cell">
                          <span className="mono text-xs bg-gray-100 px-2 py-1 rounded-lg font-medium">
                            {s.school_code}
                          </span>
                        </td>
                        <td className="td hidden lg:table-cell">
                          <span className="text-gray-500 text-xs">
                            {s.city || ""}{s.city && s.state ? ", " : ""}{s.state || ""}
                          </span>
                        </td>
                        <td className="td hidden sm:table-cell">
                          <span className="badge text-xs capitalize"
                            style={{
                              background: (PLAN_COLORS[planType] ?? "#6B7280") + "18",
                              color: PLAN_COLORS[planType] ?? "#6B7280",
                            }}>
                            {planType.replace("_", " ")}
                          </span>
                        </td>
                        <td className="td">
                          <QuotaBar pct={quotaPct} />
                        </td>
                        <td className="td hidden md:table-cell">
                          <span className="mono font-medium text-gray-700">{s.teachers || s.max_teachers || 0}</span>
                        </td>
                        <td className="td hidden lg:table-cell">
                          <span className="mono font-medium text-gray-700">{s.content_pieces || 0}</span>
                        </td>
                        <td className="td hidden xl:table-cell">
                          <span className="text-xs text-gray-400">
                            {s.created_at ? format(parseISO(s.created_at), "dd MMM yyyy") : "—"}
                          </span>
                        </td>
                        <td className="td">
                          {s.expires_at && new Date(s.expires_at) < new Date(Date.now() + 7 * 86400000) ? (
                            <span className="badge b-red flex items-center gap-1">
                              <AlertTriangle size={10} /> Expiring
                            </span>
                          ) : (
                            <span className="badge b-green flex items-center gap-1">
                              <CheckCircle2 size={10} /> Active
                            </span>
                          )}
                        </td>
                      </tr>
                      );
                    })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && (data.total_pages || data.pages || 0) > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <p className="text-sm text-gray-400">
                {(page - 1) * 20 + 1}–{Math.min(page * 20, data.total || 0)} of {data.total || 0}
              </p>
              <div className="flex items-center gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                  className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40">
                  <ChevronLeft size={14} />
                </button>
                <span className="mono text-sm font-medium">{page}/{data.total_pages || data.pages || 1}</span>
                <button onClick={() => setPage((p) => Math.min(data.total_pages || data.pages || 1, p + 1))}
                  disabled={page === (data.total_pages || data.pages || 1)}
                  className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40">
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <style jsx global>{`
        .input-field {
          width: 100%;
          padding: 10px 14px;
          border-radius: 10px;
          border: 1px solid #E5E7EB;
          font-size: 14px;
          outline: none;
          transition: all 0.15s;
          background: white;
          font-family: inherit;
        }
        .input-field:focus {
          border-color: #3B82F6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        select.input-field { cursor: pointer; }
      `}</style>
    </AdminLayout>
  );
}
