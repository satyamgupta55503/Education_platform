"use client";
// app/dashboard/alerts/page.tsx
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle, Info, RefreshCw, Clock } from "lucide-react";
import { format, parseISO } from "date-fns";
import { adminApi, SystemAlert } from "@/lib/api";
import AdminLayout from "@/components/layout/AdminLayout";
import { clsx } from "clsx";

const LEVEL_CONFIG = {
  critical: {
    icon: AlertTriangle, color: "#DC2626", bg: "#FEF2F2",
    border: "#DC2626", badge: "b-red", emoji: "🚨",
  },
  warning: {
    icon: AlertTriangle, color: "#D97706", bg: "#FFFBEB",
    border: "#D97706", badge: "b-amber", emoji: "⚠️",
  },
  info: {
    icon: Info, color: "#2563EB", bg: "#EFF6FF",
    border: "#2563EB", badge: "b-blue", emoji: "ℹ️",
  },
};

export default function AlertsPage() {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["admin-alerts"],
    queryFn: () => adminApi.getAlerts().then((r) => r.data?.data || r.data),
    refetchInterval: 30_000,
  });

  return (
    <AdminLayout>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">System Alerts</h1>
            <p className="text-sm text-gray-400">
              Auto-refreshes every 30 seconds · 7-metric monitoring
            </p>
          </div>
          <button onClick={() => refetch()}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 text-sm font-medium hover:bg-gray-50 transition-all",
              isFetching && "opacity-60 cursor-not-allowed"
            )}
            disabled={isFetching}>
            <RefreshCw size={14} className={clsx(isFetching && "animate-spin")} />
            Refresh
          </button>
        </div>

        {/* Summary cards */}
        {data && (
          <div className="grid grid-cols-3 gap-4 fade">
            <div className="card p-4 text-center">
              <p className="text-3xl font-bold text-red-500 mono">{data.critical || 0}</p>
              <p className="text-xs text-gray-400 mt-1 font-medium">Critical</p>
            </div>
            <div className="card p-4 text-center">
              <p className="text-3xl font-bold text-amber-500 mono">{data.warnings || 0}</p>
              <p className="text-xs text-gray-400 mt-1 font-medium">Warnings</p>
            </div>
            <div className="card p-4 text-center">
              <p className="text-3xl font-bold text-emerald-500 mono">{data.total || 0}</p>
              <p className="text-xs text-gray-400 mt-1 font-medium">Total</p>
            </div>
          </div>
        )}

        {/* Timestamp */}
        {data?.timestamp && (
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <Clock size={11} />
            Last checked: {format(parseISO(data.timestamp), "dd MMM yyyy HH:mm:ss")} UTC
          </div>
        )}

        {/* Alerts list */}
        {isLoading && (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card h-20 skeleton rounded-2xl" />
            ))}
          </div>
        )}

        {!isLoading && (data?.alerts || []).length === 0 && (
          <div className="card p-12 text-center fade">
            <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
            <h2 className="font-bold text-gray-800 text-lg">All Systems Healthy</h2>
            <p className="text-gray-400 text-sm mt-1">
              No alerts at this time. Platform running normally.
            </p>
          </div>
        )}

        {(data?.alerts || []).length > 0 && (
          <div className="space-y-3">
            {(data?.alerts || []).map((alert: SystemAlert, i: number) => {
              const cfg = LEVEL_CONFIG[alert.level] ?? LEVEL_CONFIG.info;
              const Icon = cfg.icon;
              return (
                <div key={i}
                  className="card p-5 fade"
                  style={{
                    borderLeft: `4px solid ${cfg.border}`,
                    background: cfg.bg,
                    animationDelay: `${i * 60}ms`,
                  }}>
                  <div className="flex items-start gap-4">
                    <div className="p-2 rounded-xl mt-0.5"
                      style={{ background: cfg.color + "18" }}>
                      <Icon size={16} style={{ color: cfg.color }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className={`badge ${cfg.badge} uppercase text-xs`}>
                          {cfg.emoji} {alert.level}
                        </span>
                        <span className="text-xs text-gray-400 mono bg-white px-2 py-0.5 rounded-lg border border-gray-100">
                          {alert.metric}
                        </span>
                      </div>
                      <p className="font-semibold text-gray-800 text-sm">
                        {alert.message}
                      </p>
                      <div className="flex items-center gap-1.5 mt-2">
                        <span className="text-xs text-gray-400">Suggested action:</span>
                        <span className="text-xs font-medium text-gray-600">{alert.action}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Monitoring metrics reference */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4 text-sm">
            📊 7 Monitored Metrics
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {[
              { name: "API Latency",      threshold: "≥ 3000ms P99",       action: "Scale up API pods" },
              { name: "Gemini Error Rate",threshold: "≥ 5% in 5 min",      action: "Activate fallback" },
              { name: "DB CPU",           threshold: "≥ 80%",              action: "Check slow queries" },
              { name: "Redis Memory",     threshold: "≥ 90% of 512MB",     action: "Evict stale keys" },
              { name: "L2 Cache Hit",     threshold: "< 25% for 1hr",      action: "Check thresholds" },
              { name: "OTP Failures",     threshold: "> 50/min",           action: "Brute-force check" },
              { name: "Celery Queue",     threshold: "> 100 tasks",        action: "Scale workers" },
            ].map((m) => (
              <div key={m.name}
                className="flex items-start gap-2.5 p-3 rounded-xl bg-gray-50 border border-gray-100">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-gray-700">{m.name}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Alert: <span className="mono">{m.threshold}</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
