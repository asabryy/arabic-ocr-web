import React, { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { updateCurrentUser } from "../features/auth/authservice";

function SettingsPage() {
  const { user, login } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [email] = useState(user?.email || "");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    setStatus("");
    const token = localStorage.getItem("access_token");
    try {
      await updateCurrentUser(token, { name });
      await login(token);
      setStatus("saved");
    } catch {
      setStatus("error");
    } finally {
      setLoading(false);
    }
  };

  const resendVerification = () => setStatus("verification_sent");

  return (
    <div className="space-y-6 animate-fade-in max-w-lg">
      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-5">
        <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">Manage your account</p>
      </div>

      <div className="border border-zinc-200 dark:border-zinc-800 border-t-2 border-t-indigo-500">
        <div className="px-5 py-4 border-b border-zinc-100 dark:border-zinc-800">
          <p className="section-label">Profile</p>
        </div>
        <div className="px-5 py-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
              Name
            </label>
            <input type="text" className="field-input" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
              Email
            </label>
            <input type="email" value={email} className="field-input opacity-50 cursor-not-allowed" disabled />
          </div>

          {!user?.is_verified && (
            <div className="flex items-start gap-2 px-3 py-2.5 bg-amber-50 dark:bg-amber-500/5 border border-amber-200 dark:border-amber-500/20 text-sm">
              <span className="text-amber-500 mt-0.5">⚠</span>
              <span className="text-amber-700 dark:text-amber-400">
                Email not verified.{" "}
                <button onClick={resendVerification} className="underline text-indigo-500 hover:text-indigo-600">
                  Resend verification email
                </button>
              </span>
            </div>
          )}

          <div className="flex items-center gap-3 pt-1">
            <button onClick={handleSave} disabled={loading} className="btn-primary px-5 py-2">
              {loading ? "Saving…" : "Save Changes"}
            </button>
            {status === "saved" && <p className="text-xs text-emerald-600 dark:text-emerald-400">Saved successfully.</p>}
            {status === "error" && <p className="text-xs text-red-500">Failed to update. Please try again.</p>}
            {status === "verification_sent" && <p className="text-xs text-indigo-500">Verification email sent.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
