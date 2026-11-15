"use client";
// app/auth/login/page.tsx  — Admin 3-step login (Email OTP → TOTP)
import { useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import toast from "react-hot-toast";
import { Shield, Lock, Mail, KeyRound, Eye, EyeOff } from "lucide-react";
import { authApi } from "@/lib/api";

type Step = "email" | "otp" | "totp";

export default function AdminLoginPage() {
  const router = useRouter();
  const [step, setStep]       = useState<Step>("email");
  const [email, setEmail]     = useState("");
  const [otp, setOtp]         = useState("");
  const [totp, setTotp]       = useState("");
  const [adminId, setAdminId] = useState("");
  const [role, setRole]       = useState("");
  const [loading, setLoading] = useState(false);
  const [showOtp, setShowOtp] = useState(false);

  const STEPS = [
    { key: "email", label: "Email", icon: Mail },
    { key: "otp",   label: "OTP",   icon: KeyRound },
    { key: "totp",  label: "TOTP",  icon: Shield },
  ] as const;
  const stepIdx = STEPS.findIndex((s) => s.key === step);

  const sendOTP = async () => {
    if (!email.includes("@")) { toast.error("Enter valid email"); return; }
    setLoading(true);
    try {
      await authApi.sendOTP(email);
      toast.success("OTP sent to your email!");
      setStep("otp");
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Failed to send OTP");
    } finally { setLoading(false); }
  };

  const verifyOTP = async () => {
    if (otp.length !== 6) { toast.error("Enter 6-digit OTP"); return; }
    setLoading(true);
    try {
      const res = await authApi.verifyOTP(email, otp);
      const d = res.data;
      if (d.status === "needs_totp") {
        setAdminId(d.admin_id);
        setRole(d.role);
        setStep("totp");
        toast("Enter your authenticator code", { icon: "🔐" });
      } else {
        Cookies.set("admin_token", d.access_token, {
          expires: d.role === "superadmin" ? 1/6 : 1/3,  // 4h / 8h
          secure: true, sameSite: "strict",
        });
        toast.success("Welcome!");
        router.push("/dashboard/overview");
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Invalid OTP");
    } finally { setLoading(false); }
  };

  const verifyTOTP = async () => {
    if (totp.length !== 6) { toast.error("Enter 6-digit code"); return; }
    setLoading(true);
    try {
      const res = await authApi.verifyTOTP(adminId, totp);
      const expireHours = role === "superadmin" ? 4 : 8;
      Cookies.set("admin_token", res.data.access_token, {
        expires: expireHours / 24,
        secure: true, sameSite: "strict",
      });
      toast.success(`Welcome, ${role}!`);
      router.push("/dashboard/overview");
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Invalid authenticator code");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex" style={{
      background: "linear-gradient(135deg, #111827 0%, #1F2937 50%, #111827 100%)",
    }}>
      {/* Left branding panel */}
      <div className="hidden lg:flex flex-col justify-center px-16 w-[420px] shrink-0">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl mb-6"
          style={{ background: "linear-gradient(135deg, #2563EB, #7C3AED)" }}>
          🐱
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">EduCat AI</h1>
        <p className="text-white/50 text-sm mb-8">Admin Control Center</p>

        <div className="space-y-4">
          {[
            { icon: "🏫", label: "Manage all school workspaces" },
            { icon: "👥", label: "User & subscription control" },
            { icon: "📊", label: "Platform-wide analytics" },
            { icon: "⚡", label: "Real-time cache monitoring" },
            { icon: "🚨", label: "7-metric alert system" },
          ].map((f) => (
            <div key={f.label} className="flex items-center gap-3">
              <span className="text-xl">{f.icon}</span>
              <span className="text-white/60 text-sm">{f.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-[400px]">
          {/* Mobile logo */}
          <div className="text-center mb-8 lg:hidden">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-3"
              style={{ background: "linear-gradient(135deg, #2563EB, #7C3AED)" }}>
              🐱
            </div>
            <h1 className="text-2xl font-bold text-white">EduCat Admin</h1>
          </div>

          {/* Step indicator */}
          <div className="flex items-center mb-8">
            {STEPS.map((s, i) => {
              const Icon   = s.icon;
              const done   = i < stepIdx;
              const active = i === stepIdx;
              return (
                <div key={s.key} className="flex items-center flex-1 last:flex-none">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                    done   ? "bg-emerald-500 text-white" :
                    active ? "bg-blue-600 text-white" :
                             "bg-white/10 text-white/30"
                  }`}>
                    {done ? "✓" : <Icon size={14} />}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className={`flex-1 h-0.5 mx-2 transition-all ${
                      done ? "bg-emerald-500" : "bg-white/10"
                    }`} />
                  )}
                </div>
              );
            })}
          </div>

          {/* Form card */}
          <div className="bg-white rounded-2xl p-7 shadow-2xl">
            {/* Email step */}
            {step === "email" && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Admin Sign In</h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Enter your admin email address
                  </p>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block mb-1.5">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="email" value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && sendOTP()}
                      placeholder="admin@educat.ai"
                      className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
                    />
                  </div>
                </div>
                <button onClick={sendOTP} disabled={loading}
                  className="w-full py-3 rounded-xl font-bold text-white text-sm transition-all hover:opacity-90 disabled:opacity-50"
                  style={{ background: "linear-gradient(135deg, #2563EB, #1D4ED8)" }}>
                  {loading ? "Sending OTP..." : "Continue →"}
                </button>
              </div>
            )}

            {/* OTP step */}
            {step === "otp" && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Enter OTP</h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    Sent to <span className="font-medium text-gray-700">{email}</span>
                    <span className="text-gray-400"> · 5 minutes</span>
                  </p>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block mb-1.5">
                    One-Time Password
                  </label>
                  <div className="relative">
                    <input
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g,"").slice(0,6))}
                      onKeyDown={(e) => e.key === "Enter" && verifyOTP()}
                      type={showOtp ? "text" : "password"}
                      placeholder="● ● ● ● ● ●"
                      maxLength={6}
                      className="w-full px-4 py-4 rounded-xl border border-gray-200 text-center text-2xl font-bold tracking-[0.3em] outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
                    />
                    <button type="button" onClick={() => setShowOtp(!showOtp)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                      {showOtp ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <button onClick={verifyOTP} disabled={loading || otp.length !== 6}
                  className="w-full py-3 rounded-xl font-bold text-white text-sm transition-all hover:opacity-90 disabled:opacity-50"
                  style={{ background: "linear-gradient(135deg, #059669, #047857)" }}>
                  {loading ? "Verifying..." : "Verify OTP →"}
                </button>
                <button onClick={() => setStep("email")}
                  className="w-full py-2 text-sm text-gray-400 hover:text-gray-600 transition-colors">
                  ← Back to email
                </button>
              </div>
            )}

            {/* TOTP step */}
            {step === "totp" && (
              <div className="space-y-5">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Shield size={18} className="text-violet-600" />
                    <h2 className="text-lg font-bold text-gray-900">Authenticator Code</h2>
                  </div>
                  <p className="text-sm text-gray-500">
                    Enter the 6-digit code from Google Authenticator
                  </p>
                </div>
                <div className="p-3 rounded-xl flex items-center gap-2 text-sm"
                  style={{ background: "#F5F3FF", border: "1px solid #DDD6FE" }}>
                  <Lock size={13} className="text-violet-600 shrink-0" />
                  <span className="text-violet-700 text-xs font-medium">
                    {role === "superadmin"
                      ? "SuperAdmin: TOTP required. 4-hour session."
                      : "2FA required for your account security."}
                  </span>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block mb-1.5">
                    Authenticator Code
                  </label>
                  <input
                    value={totp}
                    onChange={(e) => setTotp(e.target.value.replace(/\D/g,"").slice(0,6))}
                    onKeyDown={(e) => e.key === "Enter" && verifyTOTP()}
                    type="text" inputMode="numeric"
                    placeholder="000 000"
                    maxLength={7}
                    className="w-full px-4 py-4 rounded-xl border border-gray-200 text-center text-2xl font-bold tracking-[0.3em] outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100 transition-all"
                  />
                </div>
                <button onClick={verifyTOTP}
                  disabled={loading || totp.replace(/\s/g,"").length !== 6}
                  className="w-full py-3 rounded-xl font-bold text-white text-sm transition-all hover:opacity-90 disabled:opacity-50"
                  style={{ background: "linear-gradient(135deg, #7C3AED, #6D28D9)" }}>
                  {loading ? "Verifying..." : "Access Dashboard →"}
                </button>
              </div>
            )}
          </div>

          <p className="text-center text-white/20 text-xs mt-6">
            EduCat AI Admin Portal · 3-Factor Secured
          </p>
        </div>
      </div>
    </div>
  );
}
