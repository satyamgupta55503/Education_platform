"use client";
// components/layout/DashboardLayout.tsx
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import {
  LayoutDashboard, Users, BookOpen, GraduationCap,
  BarChart3, AlertTriangle, Upload, LogOut,
  Menu, X, ChevronRight, Wifi, Bell, Settings,
} from "lucide-react";
import { clsx } from "clsx";
import { schoolApi } from "@/lib/api";

// ── Nav items ─────────────────────────────────────────────────────────────────
const NAV = [
  { href: "/dashboard/overview",  icon: LayoutDashboard, label: "Overview",       badge: null },
  { href: "/dashboard/students",  icon: Users,            label: "Students",       badge: null },
  { href: "/dashboard/teachers",  icon: GraduationCap,   label: "Teachers",       badge: null },
  { href: "/dashboard/subjects",  icon: BookOpen,        label: "Subjects",       badge: null },
  { href: "/dashboard/content",   icon: Upload,          label: "Content",        badge: null },
  { href: "/dashboard/reports",   icon: BarChart3,       label: "Reports",        badge: null },
];

// ── Workspace info from cookie ─────────────────────────────────────────────────
interface WorkspaceInfo {
  school_name: string; school_code: string; plan_type: string;
  quota_used_pct: number;
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router   = useRouter();
  const [open, setOpen]         = useState(false);
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [notifCount, setNotifCount] = useState(0);

  useEffect(() => {
    schoolApi.getOverview().then((r) => {
      const w = r.data.workspace;
      setWorkspace({
        school_name: w.school_name,
        school_code: w.school_code,
        plan_type: w.plan_type,
        quota_used_pct: w.quota_used_pct,
      });
    }).catch(() => {});
  }, []);

  const handleLogout = useCallback(async () => {
    try { await import("@/lib/api").then(m => m.authApi.logout()); } catch (_) {}
    Cookies.remove("teacher_token");
    router.push("/auth/login");
  }, [router]);

  const sidebar = (
    <aside
      className="flex flex-col h-full"
      style={{ background: "linear-gradient(180deg, #0F1729 0%, #1A2744 100%)" }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-white/10">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center text-xl"
          style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}>
          🐱
        </div>
        <div>
          <p className="text-white font-bold text-sm leading-none">EduCat AI</p>
          <p className="text-white/40 text-xs mt-0.5">School Portal</p>
        </div>
      </div>

      {/* School info */}
      {workspace && (
        <div className="mx-4 mt-4 p-3 rounded-xl border border-white/10 bg-white/5">
          <p className="text-white font-semibold text-sm truncate">{workspace.school_name}</p>
          <p className="text-white/50 text-xs mt-0.5">{workspace.school_code} · {workspace.plan_type}</p>
          <div className="mt-2.5">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-white/40">Monthly quota</span>
              <span className="text-white/70 font-medium num">{workspace.quota_used_pct}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/10">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(workspace.quota_used_pct, 100)}%`,
                  background: workspace.quota_used_pct > 80
                    ? "#EF4444" : workspace.quota_used_pct > 60
                    ? "#F59E0B" : "#10B981",
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV.map(({ href, icon: Icon, label, badge }) => (
          <Link
            key={href} href={href}
            onClick={() => setOpen(false)}
            className={clsx("nav-link", pathname.startsWith(href) && "active")}
          >
            <Icon size={17} className="icon shrink-0" />
            <span className="flex-1">{label}</span>
            {badge && (
              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-red-500 text-white">{badge}</span>
            )}
            {pathname.startsWith(href) && (
              <ChevronRight size={13} className="text-white/40" />
            )}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-white/10 space-y-0.5">
        <Link href="/dashboard/settings"
          className={clsx("nav-link", pathname.includes("settings") && "active")}>
          <Settings size={17} className="icon" />
          <span>Settings</span>
        </Link>
        <button onClick={handleLogout} className="nav-link w-full text-left text-red-400 hover:text-red-300">
          <LogOut size={17} className="icon !text-red-400" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Desktop sidebar */}
      <div className="hidden lg:flex flex-col shrink-0" style={{ width: "var(--sidebar-w)" }}>
        {sidebar}
      </div>

      {/* Mobile sidebar overlay */}
      {open && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setOpen(false)} />
          <div className="relative z-10 flex flex-col h-full" style={{ width: "var(--sidebar-w)" }}>
            {sidebar}
          </div>
          <button onClick={() => setOpen(false)}
            className="absolute top-4 right-4 z-20 p-2 rounded-full bg-white shadow-lg">
            <X size={18} />
          </button>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="shrink-0 h-16 bg-white border-b border-gray-100 flex items-center px-4 lg:px-6 gap-4">
          <button onClick={() => setOpen(true)}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <Menu size={20} />
          </button>

          {/* Breadcrumb */}
          <div className="hidden sm:flex items-center gap-2 text-sm flex-1">
            <span className="text-gray-400">School</span>
            <ChevronRight size={14} className="text-gray-300" />
            <span className="font-medium text-gray-700 capitalize">
              {pathname.split("/").pop()?.replace(/-/g, " ") ?? "Dashboard"}
            </span>
          </div>

          <div className="flex-1 sm:flex-none" />

          {/* Online indicator */}
          <div className="flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-full">
            <Wifi size={12} />
            <span className="hidden sm:block font-medium">Connected</span>
          </div>

          {/* Notifications */}
          <button className="relative p-2 rounded-xl hover:bg-gray-100 transition-colors">
            <Bell size={18} className="text-gray-500" />
            {notifCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 rounded-full text-white text-xs flex items-center justify-center">
                {notifCount}
              </span>
            )}
          </button>
        </header>

        {/* Page */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
