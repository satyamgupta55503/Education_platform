"use client";
// app/dashboard/layout.tsx — Dark-themed dashboard shell with sidebar + topbar
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { clsx } from "clsx";
import toast from "react-hot-toast";
import { authApi } from "@/lib/api";

// ── Navigation items ──────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { href: "/dashboard/overview",  emoji: "📊", label: "Overview" },
  { href: "/dashboard/students",  emoji: "👥", label: "Students" },
  { href: "/dashboard/teachers",  emoji: "👨‍🏫", label: "Teachers" },
  { href: "/dashboard/subjects",  emoji: "📚", label: "Subjects" },
  { href: "/dashboard/content",   emoji: "📄", label: "Content" },
  { href: "/dashboard/live",      emoji: "🎓", label: "Live Lesson" },
  { href: "/dashboard/analytics", emoji: "📈", label: "Analytics" },
];

export default function DashboardShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [teacherName, setTeacherName] = useState("");
  const [schoolName, setSchoolName] = useState("");

  // Load teacher info from cookie
  useEffect(() => {
    const token = Cookies.get("teacher_token");
    if (!token) {
      router.push("/auth/login");
      return;
    }
    setTeacherName(Cookies.get("teacher_name") || "Teacher");
    setSchoolName(Cookies.get("school_name") || "EduCat AI School");
  }, [router]);

  const handleLogout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (_) {}
    Cookies.remove("teacher_token");
    Cookies.remove("teacher_name");
    Cookies.remove("workspace_id");
    Cookies.remove("school_name");
    toast.success("Logged out successfully");
    router.push("/auth/login");
  }, [router]);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-900">
      {/* ── Desktop Sidebar ──────────────────────────────────────────── */}
      <aside className="hidden lg:flex flex-col w-64 shrink-0 bg-slate-950 border-r border-white/5">
        {/* Logo header */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-white/5">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-xl shadow-lg"
            style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
          >
            🐱
          </div>
          <div>
            <p className="text-white font-bold text-sm leading-tight">EduCat AI</p>
            <p className="text-slate-500 text-xs">School Portal</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(({ href, emoji, label }) => {
            const isActive = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-blue-500/15 text-blue-400 shadow-sm"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                )}
              >
                <span className="text-base">{emoji}</span>
                <span>{label}</span>
                {isActive && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Sidebar footer */}
        <div className="px-3 py-4 border-t border-white/5 space-y-1">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all w-full"
          >
            <span className="text-base">🚪</span>
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* ── Mobile Sidebar Overlay ───────────────────────────────────── */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative z-10 flex flex-col w-64 bg-slate-950 h-full shadow-2xl">
            {/* Logo */}
            <div className="flex items-center justify-between px-5 py-5 border-b border-white/5">
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-lg"
                  style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
                >
                  🐱
                </div>
                <p className="text-white font-bold text-sm">EduCat AI</p>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Nav */}
            <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
              {NAV_ITEMS.map(({ href, emoji, label }) => {
                const isActive = pathname === href || pathname.startsWith(href + "/");
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setSidebarOpen(false)}
                    className={clsx(
                      "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all",
                      isActive
                        ? "bg-blue-500/15 text-blue-400"
                        : "text-slate-400 hover:bg-white/5 hover:text-white"
                    )}
                  >
                    <span className="text-base">{emoji}</span>
                    <span>{label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Logout */}
            <div className="px-3 py-4 border-t border-white/5">
              <button
                onClick={handleLogout}
                className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-red-400 hover:bg-red-500/10 w-full"
              >
                <span>🚪</span>
                <span>Logout</span>
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* ── Main Area ────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="shrink-0 h-16 bg-slate-900 border-b border-white/5 flex items-center px-4 lg:px-6 gap-4">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* School name */}
          <div className="flex-1 flex items-center gap-3">
            <div className="hidden sm:block">
              <p className="text-white font-semibold text-sm">{schoolName}</p>
              <p className="text-slate-500 text-xs">
                {pathname.split("/").pop()?.replace(/-/g, " ").replace(/^\w/, (c) => c.toUpperCase()) || "Dashboard"}
              </p>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {/* Online status */}
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-medium">Live</span>
            </div>

            {/* Teacher avatar */}
            <div className="flex items-center gap-2 pl-3 border-l border-white/10">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-white text-xs font-bold">
                {teacherName.charAt(0).toUpperCase()}
              </div>
              <span className="hidden sm:block text-sm text-slate-300 font-medium">
                {teacherName}
              </span>
            </div>

            {/* Logout button */}
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
              title="Logout"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6 bg-slate-900">
          {children}
        </main>
      </div>

      {/* ── Floating Cat Chatbot Button ──────────────────────────────── */}
      <button
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-2xl flex items-center justify-center text-2xl hover:scale-110 transition-transform z-40 border border-white/10"
        style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
        title="Ask EduCat AI"
      >
        🐱
      </button>
    </div>
  );
}
