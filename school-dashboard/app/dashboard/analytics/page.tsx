"use client";
// app/dashboard/analytics/page.tsx — Analytics placeholder page

export default function AnalyticsPage() {
  return (
    <div className="flex items-center justify-center h-[calc(100vh-8rem)]">
      <div className="text-center">
        <div
          className="w-20 h-20 rounded-2xl mx-auto mb-6 flex items-center justify-center text-4xl shadow-lg border border-white/5"
          style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
        >
          📈
        </div>
        <h1 className="text-2xl font-bold text-white">Analytics coming soon</h1>
        <p className="text-slate-400 text-sm mt-3 max-w-md mx-auto">
          We&apos;re building powerful analytics to help you track student progress,
          engagement patterns, and learning outcomes.
        </p>
        <div className="mt-6 flex items-center justify-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          <span className="text-xs text-slate-500 font-medium">In Development</span>
        </div>
      </div>
    </div>
  );
}
