"use client";
// components/layout/AdminLayout.tsx
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import {
  LayoutDashboard, Building2, Users, DollarSign,
  Zap, AlertTriangle, BookOpen, LogOut, Menu, X,
  ChevronRight, Bell, Shield, Settings,
} from "lucide-react";
import { clsx } from "clsx";
import { adminApi } from "@/lib/api";

const NAV = [
  { href: "/dashboard/overview", icon: LayoutDashboard, label: "Overview"   },
  { href: "/dashboard/schools",  icon: Building2,       label: "Schools"    },
  { href: "/dashboard/users",    icon: Users,           label: "Users"      },
  { href: "/dashboard/revenue",  icon: DollarSign,      label: "Revenue"    },
  { href: "/dashboard/cache",    icon: Zap,             label: "Cache"      },
  { href: "/dashboard/alerts",   icon: AlertTriangle,   label: "Alerts"     },
  { href: "/dashboard/content",  icon: BookOpen,        label: "Content"    },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router   = useRouter();
  const [open, setOpen]         = useState(false);
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    adminApi.getAlerts().then((r) => setAlertCount(r.data.critical)).catch(() => {});
  }, []);

  const handleLogout = useCallback(async () => {
    try { await adminApi.getAlerts(); } catch (_) {}
    Cookies.remove("admin_token");
    router.push("/auth/login");
  }, [router]);

  const Sidebar = (
    <div
      className="flex flex-col h-full"
      style={{ background: "#111827" }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/10">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-lg"
          style={{ background: "linear-gradient(135deg, #2563EB, #7C3AED)" }}>
          🐱
        </div>
        <div>
          <p className="text-white font-bold text-sm">EduCat AI</p>
          <p className="text-white/40 text-xs flex items-center gap-1">
            <Shield size={10} /> Admin Portal
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {NAV.map(({ href, icon: Icon, label }) => (
          <Link key={href} href={href}
            onClick={() => setOpen(false)}
            className={clsx("snav", pathname.startsWith(href) && "active")}>
            <Icon size={16} className="sicon" />
            <span className="flex-1">{label}</span>
            {label === "Alerts" && alertCount > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-xs font-bold bg-red-500 text-white">
                {alertCount}
              </span>
            )}
            {pathname.startsWith(href) && (
              <ChevronRight size={12} className="opacity-60" />
            )}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 pb-4 pt-2 border-t border-white/10 space-y-0.5">
        <Link href="/dashboard/settings"
          className={clsx("snav", pathname.includes("settings") && "active")}>
          <Settings size={16} className="sicon" />
          <span>Settings</span>
        </Link>
        <button onClick={handleLogout} className="snav text-red-400 hover:text-red-300 hover:!bg-red-900/30">
          <LogOut size={16} className="sicon !text-red-400" />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>
      {/* Desktop sidebar */}
      <div className="hidden lg:block shrink-0 w-56">
        {Sidebar}
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <div className="relative z-10 w-56 h-full">{Sidebar}</div>
          <button className="absolute top-3 right-3 z-20 p-2 rounded-full bg-white"
            onClick={() => setOpen(false)}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="shrink-0 h-14 bg-white border-b border-gray-100 flex items-center px-4 gap-4">
          <button className="lg:hidden p-1.5 rounded-lg hover:bg-gray-100"
            onClick={() => setOpen(true)}>
            <Menu size={18} />
          </button>
          <div className="flex items-center gap-2 text-sm flex-1 hidden sm:flex">
            <span className="text-gray-400 text-xs">Admin</span>
            <ChevronRight size={12} className="text-gray-300" />
            <span className="font-semibold text-gray-700 capitalize text-sm">
              {pathname.split("/").pop()?.replace(/-/g, " ") ?? "Dashboard"}
            </span>
          </div>
          <div className="flex-1 sm:flex-none" />
          <div className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-semibold"
            style={{ background: "#EFF6FF", color: "#2563EB" }}>
            <Shield size={11} /> Superadmin
          </div>
          <button className="relative p-2 rounded-xl hover:bg-gray-50">
            <Bell size={16} className="text-gray-500" />
            {alertCount > 0 && (
              <span className="absolute top-1 right-1 w-3.5 h-3.5 bg-red-500 rounded-full text-white text-xs flex items-center justify-center font-bold">
                {alertCount}
              </span>
            )}
          </button>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
