"use client";
import { useState } from "react";
import Cookies from "js-cookie";
import toast from "react-hot-toast";
import { Shield, User, Key, Bell, Database } from "lucide-react";
import AdminLayout from "@/components/layout/AdminLayout";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");
  const adminName = "Super Admin";
  const adminEmail = "admin@educate.ai";
  const role = Cookies.get("admin_role") || "superadmin";

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "security", label: "Security", icon: Shield },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "system", label: "System", icon: Database },
  ];

  return (
    <AdminLayout>
      <div className="space-y-5 max-w-4xl">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Settings</h1>
          <p className="text-sm text-gray-400">Manage your admin account and platform settings</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center ${
                activeTab === id
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Icon size={14} />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* Profile Tab */}
        {activeTab === "profile" && (
          <div className="card p-6 space-y-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-white text-2xl font-bold">
                {adminName.charAt(0)}
              </div>
              <div>
                <h2 className="font-bold text-gray-900 text-lg">{adminName}</h2>
                <p className="text-sm text-gray-500">{adminEmail}</p>
                <span className="inline-block mt-1 px-2.5 py-0.5 rounded-lg text-xs font-semibold bg-violet-100 text-violet-700 capitalize">
                  {role}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-gray-100">
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-1.5">Name</label>
                <input defaultValue={adminName} className="input-field" readOnly />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-1.5">Email</label>
                <input defaultValue={adminEmail} className="input-field" readOnly />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-1.5">Role</label>
                <input defaultValue={role} className="input-field capitalize" readOnly />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-1.5">Last Login</label>
                <input defaultValue={new Date().toLocaleDateString()} className="input-field" readOnly />
              </div>
            </div>
          </div>
        )}

        {/* Security Tab */}
        {activeTab === "security" && (
          <div className="space-y-4">
            <div className="card p-6">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-blue-50">
                  <Key size={20} className="text-blue-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">TOTP Two-Factor Authentication</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    Required for SuperAdmin accounts. Use Google Authenticator or any TOTP app.
                  </p>
                  <div className="mt-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    <span className="text-xs text-amber-600 font-medium">Not configured (dev mode bypasses TOTP)</span>
                  </div>
                </div>
                <button
                  disabled
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-white bg-blue-600 opacity-50 cursor-not-allowed"
                >
                  Setup TOTP
                </button>
              </div>
            </div>

            <div className="card p-6">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-red-50">
                  <Shield size={20} className="text-red-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">Active Sessions</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    Manage your active login sessions across devices.
                  </p>
                  <div className="mt-3 p-3 bg-gray-50 rounded-xl">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-700">Current Session</p>
                        <p className="text-xs text-gray-400">Browser · {new Date().toLocaleString()}</p>
                      </div>
                      <span className="px-2 py-0.5 rounded-lg text-xs font-semibold bg-emerald-100 text-emerald-700">Active</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Notifications Tab */}
        {activeTab === "notifications" && (
          <div className="card p-6 space-y-5">
            <h3 className="font-semibold text-gray-900">Notification Preferences</h3>
            {[
              { label: "Safety queue alerts", desc: "When flagged messages exceed threshold", checked: true },
              { label: "Workspace quota warnings", desc: "Schools approaching monthly limit", checked: true },
              { label: "New user milestones", desc: "When platform reaches user milestones", checked: false },
              { label: "System health alerts", desc: "Redis/DB/API performance issues", checked: true },
              { label: "Revenue updates", desc: "Daily subscription revenue summary", checked: false },
            ].map((n) => (
              <div key={n.label} className="flex items-center justify-between py-3 border-b border-gray-50 last:border-0">
                <div>
                  <p className="text-sm font-medium text-gray-800">{n.label}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{n.desc}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked={n.checked} className="sr-only peer" onChange={() => toast.success("Preference saved")} />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
            ))}
          </div>
        )}

        {/* System Tab */}
        {activeTab === "system" && (
          <div className="space-y-4">
            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Platform Information</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  { label: "Backend Version", value: "3.0.0" },
                  { label: "Environment", value: "Development" },
                  { label: "Database", value: "Supabase PostgreSQL" },
                  { label: "Cache", value: "Redis Cloud" },
                  { label: "AI Model", value: "Gemini 2.5 Flash" },
                  { label: "Vector Store", value: "pgvector (HNSW)" },
                ].map((item) => (
                  <div key={item.label} className="p-3 bg-gray-50 rounded-xl">
                    <p className="text-xs text-gray-500 font-medium">{item.label}</p>
                    <p className="text-sm font-semibold text-gray-800 mt-0.5 mono">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-3">Danger Zone</h3>
              <div className="p-4 bg-red-50 border border-red-100 rounded-xl">
                <p className="text-sm text-red-700 font-medium">Clear All Caches</p>
                <p className="text-xs text-red-500 mt-1">This will clear Redis L1 cache, semantic cache, and audio cache. Operations will be slower temporarily.</p>
                <button
                  onClick={() => toast.error("Not available in development mode")}
                  className="mt-3 px-4 py-2 rounded-lg text-xs font-semibold text-red-600 border border-red-200 hover:bg-red-100 transition-colors"
                >
                  Clear All Caches
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx global>{`
        .input-field {
          width: 100%; padding: 10px 14px; border-radius: 10px;
          border: 1px solid #E5E7EB; font-size: 14px; outline: none;
          transition: all 0.15s; background: #F9FAFB; font-family: inherit;
        }
        .input-field:focus { border-color: #3B82F6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); background: white; }
      `}</style>
    </AdminLayout>
  );
}
