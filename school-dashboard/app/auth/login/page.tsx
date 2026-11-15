"use client";
// app/auth/login/page.tsx — School Teacher Login (OTP → Dashboard)
import { useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import toast from "react-hot-toast";
import { authApi } from "@/lib/api";

function getDeviceFingerprint(): string {
  if (typeof window === "undefined") return "server";
  const raw = [
    navigator.userAgent, screen.width, screen.height,
    Intl.DateTimeFormat().resolvedOptions().timeZone,
  ].join("|");
  let hash = 0;
  for (let i = 0; i < raw.length; i++) {
    hash = ((hash << 5) - hash) + raw.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash).toString(16).padStart(8, "0").toUpperCase();
}

export default function SchoolLoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<"credentials" | "otp" | "totp">("credentials");
  const [email, setEmail] = useState("");
  const [wsId, setWsId] = useState("");
  const [otp, setOtp] = useState("");
  const [totp, setTotp] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [qrUrl, setQrUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const fp = typeof window !== "undefined" ? getDeviceFingerprint() : "";

  // Step 1: Send OTP
  const handleSendOTP = async () => {
    if (!email.trim() || !wsId.trim()) {
      toast.error("Enter workspace ID and email");
      return;
    }
    setLoading(true);
    try {
      await authApi.sendOTP(email.trim(), wsId.trim());
      toast.success("OTP sent! Check your email.");
      setStep("otp");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to send OTP. Check your credentials.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Verify OTP
  const handleVerifyOTP = async () => {
    if (otp.length !== 6) {
      toast.error("Enter 6-digit OTP");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.verifyOTP(email.trim(), wsId.trim(), otp, fp, "School Browser");
      const data = res.data;

      // Check if TOTP setup/verification is needed
      if (data.requires_totp || data.needs_totp_setup) {
        setTeacherId(data.teacher_id);
        if (data.needs_totp_setup) {
          // First-time TOTP setup — get QR code
          const qrRes = await authApi.getTOTPSetup(data.teacher_id, email);
          setQrUrl(qrRes.data.qr_code_data_url);
          toast("Scan the QR code with Google Authenticator", { icon: "📱" });
        } else {
          toast("Enter your authenticator code", { icon: "🔐" });
        }
        setStep("totp");
      } else {
        // Success — save token and redirect
        Cookies.set("teacher_token", data.access_token, { expires: 1 });
        if (data.teacher_name) {
          Cookies.set("teacher_name", data.teacher_name, { expires: 1 });
        }
        if (data.workspace_id) {
          Cookies.set("workspace_id", data.workspace_id, { expires: 1 });
        }
        toast.success(`Welcome, ${data.teacher_name || "Teacher"}!`);
        router.push("/dashboard/overview");
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Invalid OTP. Please try again.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Verify TOTP (if required)
  const handleVerifyTOTP = async () => {
    if (totp.length !== 6) {
      toast.error("Enter 6-digit authenticator code");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.verifyTOTP(teacherId, wsId.trim(), totp, fp, "School Browser");
      const data = res.data;
      Cookies.set("teacher_token", data.access_token, { expires: 1 });
      if (data.teacher_name) {
        Cookies.set("teacher_name", data.teacher_name, { expires: 1 });
      }
      toast.success("Authentication complete!");
      router.push("/dashboard/overview");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Invalid authenticator code";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  // Handle Enter key
  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === "Enter" && !loading) action();
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: "linear-gradient(135deg, #0F1729 0%, #1A2744 50%, #0F1729 100%)" }}
    >
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div
            className="w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center text-3xl shadow-2xl"
            style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
          >
            🐱
          </div>
          <h1 className="text-2xl font-bold text-white">EduCat AI</h1>
          <p className="text-white/50 text-sm mt-1">School Teacher Portal</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl p-7 shadow-2xl">
          {/* Step indicator */}
          <div className="flex items-center gap-2 mb-6">
            {["credentials", "otp", "totp"].map((s, i) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    step === s
                      ? "bg-blue-500 text-white scale-110"
                      : (["credentials", "otp", "totp"].indexOf(step) > i)
                        ? "bg-emerald-500 text-white"
                        : "bg-gray-200 text-gray-400"
                  }`}
                >
                  {["credentials", "otp", "totp"].indexOf(step) > i ? "✓" : i + 1}
                </div>
                {i < 2 && (
                  <div className={`w-8 h-0.5 rounded ${
                    ["credentials", "otp", "totp"].indexOf(step) > i ? "bg-emerald-500" : "bg-gray-200"
                  }`} />
                )}
              </div>
            ))}
          </div>

          {/* STEP 1: Workspace + Email */}
          {step === "credentials" && (
            <div className="space-y-4" onKeyDown={(e) => handleKeyDown(e, handleSendOTP)}>
              <div>
                <h2 className="font-bold text-lg text-gray-900">Sign In</h2>
                <p className="text-sm text-gray-500 mt-0.5">Enter your school workspace and email</p>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">
                    Workspace ID
                  </label>
                  <input
                    value={wsId}
                    onChange={(e) => setWsId(e.target.value)}
                    placeholder="e.g. DPS-DEL-001"
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">
                    Teacher Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="teacher@school.edu"
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
                  />
                </div>
              </div>
              <button
                onClick={handleSendOTP}
                disabled={loading}
                className="w-full py-3 rounded-xl font-semibold text-white text-sm transition-all disabled:opacity-60 hover:opacity-90 active:scale-[0.98]"
                style={{ background: "linear-gradient(135deg, #3B82F6, #2563EB)" }}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Sending OTP...
                  </span>
                ) : (
                  "Send OTP →"
                )}
              </button>
              {/* Dev mode hint */}
              {process.env.NODE_ENV === "development" && (
                <p className="text-xs text-center text-gray-400 mt-2">
                  Dev mode: OTP is <span className="font-mono font-bold text-blue-500">123456</span>
                </p>
              )}
            </div>
          )}

          {/* STEP 2: OTP Verification */}
          {step === "otp" && (
            <div className="space-y-4" onKeyDown={(e) => handleKeyDown(e, handleVerifyOTP)}>
              <div>
                <h2 className="font-bold text-lg text-gray-900">Enter OTP</h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  Sent to <span className="font-medium text-gray-700">{email}</span>
                </p>
              </div>
              <input
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="● ● ● ● ● ●"
                className="w-full px-4 py-4 rounded-xl border border-gray-200 text-center text-2xl font-bold tracking-widest outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
                maxLength={6}
                autoFocus
              />
              <button
                onClick={handleVerifyOTP}
                disabled={loading || otp.length !== 6}
                className="w-full py-3 rounded-xl font-semibold text-white text-sm transition-all disabled:opacity-60 hover:opacity-90 active:scale-[0.98]"
                style={{ background: "linear-gradient(135deg, #10B981, #059669)" }}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Verifying...
                  </span>
                ) : (
                  "Verify OTP →"
                )}
              </button>
              <div className="flex items-center justify-between">
                <button
                  onClick={() => { setStep("credentials"); setOtp(""); }}
                  className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
                >
                  ← Back
                </button>
                <button
                  onClick={handleSendOTP}
                  disabled={loading}
                  className="text-sm text-blue-500 hover:text-blue-600 font-medium transition-colors disabled:opacity-50"
                >
                  Resend OTP
                </button>
              </div>
              {/* Dev mode hint */}
              {process.env.NODE_ENV === "development" && (
                <p className="text-xs text-center text-gray-400">
                  Dev mode: OTP is <span className="font-mono font-bold text-blue-500">123456</span>
                </p>
              )}
            </div>
          )}

          {/* STEP 3: TOTP (if required) */}
          {step === "totp" && (
            <div className="space-y-4" onKeyDown={(e) => handleKeyDown(e, handleVerifyTOTP)}>
              <div>
                <h2 className="font-bold text-lg text-gray-900">
                  {qrUrl ? "Setup Authenticator" : "Authenticator Code"}
                </h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  {qrUrl
                    ? "Scan this QR with Google Authenticator, then enter the code"
                    : "Enter the 6-digit code from your authenticator app"}
                </p>
              </div>
              {qrUrl && (
                <div className="flex justify-center p-4 bg-gray-50 rounded-xl">
                  <img src={qrUrl} alt="TOTP QR Code" className="w-44 h-44 rounded-lg" />
                </div>
              )}
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 block">
                  6-digit code
                </label>
                <input
                  value={totp}
                  onChange={(e) => setTotp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="● ● ● ● ● ●"
                  className="w-full px-4 py-4 rounded-xl border border-gray-200 text-center text-2xl font-bold tracking-widest outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100 transition-all"
                  maxLength={6}
                  autoFocus
                />
              </div>
              <button
                onClick={handleVerifyTOTP}
                disabled={loading || totp.length !== 6}
                className="w-full py-3 rounded-xl font-semibold text-white text-sm transition-all disabled:opacity-60 hover:opacity-90 active:scale-[0.98]"
                style={{ background: "linear-gradient(135deg, #8B5CF6, #7C3AED)" }}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Verifying...
                  </span>
                ) : (
                  "Access Dashboard →"
                )}
              </button>
              <button
                onClick={() => { setStep("otp"); setTotp(""); }}
                className="w-full py-2 text-sm text-gray-400 hover:text-gray-600 transition-colors"
              >
                ← Back to OTP
              </button>
            </div>
          )}
        </div>

        <p className="text-center text-white/30 text-xs mt-6">
          EduCat AI School Portal · Secure Authentication
        </p>
      </div>
    </div>
  );
}
