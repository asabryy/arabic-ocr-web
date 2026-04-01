import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";
import { resetPassword } from "../features/auth/authservice";

const PASSWORD_RULES = [
  { key: "minLength", label: "At least 8 characters",        test: (p) => p.length >= 8 },
  { key: "uppercase", label: "One uppercase letter (A–Z)",   test: (p) => /[A-Z]/.test(p) },
  { key: "number",    label: "One number (0–9)",             test: (p) => /[0-9]/.test(p) },
  { key: "special",   label: "One special character (!@#…)", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [form, setForm] = useState({ new_password: "", confirm: "" });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  if (!token) {
    return (
      <div className="text-center space-y-4">
        <h1 className="text-2xl font-bold tracking-tight">Invalid link</h1>
        <p className="text-sm text-muted-foreground">
          This password reset link is missing a token.
        </p>
        <Link to="/forgot-password" className="text-sm text-accent hover:text-accent-hover transition-colors">
          Request a new link
        </Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="text-center space-y-5">
        <div className="w-12 h-12 bg-success-subtle flex items-center justify-center mx-auto" style={{ borderRadius: 2 }}>
          <CheckCircle className="w-6 h-6 text-success" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Password updated</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Your password has been changed successfully.
          </p>
        </div>
        <Link to="/login" className="inline-block text-sm font-medium text-accent hover:text-accent-hover transition-colors">
          Sign in
        </Link>
      </div>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    const allPass = PASSWORD_RULES.every((r) => r.test(form.new_password));
    if (!allPass) {
      toast.error("Password doesn't meet the requirements.");
      return;
    }
    if (form.new_password !== form.confirm) {
      toast.error("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await resetPassword({ token, new_password: form.new_password });
      setDone(true);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Reset failed. The link may be expired.");
    } finally {
      setLoading(false);
    }
  };

  const passRules = PASSWORD_RULES.map((r) => ({ ...r, ok: r.test(form.new_password) }));
  const strength = passRules.filter((r) => r.ok).length;
  const strengthColor = ["bg-error", "bg-warning", "bg-warning", "bg-success", "bg-success"][strength];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Set new password</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Choose a strong password for your account.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
            New password
          </label>
          <div className="relative">
            <input
              type={showPass ? "text" : "password"}
              required
              value={form.new_password}
              onChange={(e) => setForm({ ...form, new_password: e.target.value })}
              className="field-input pr-10"
            />
            <button
              type="button"
              onClick={() => setShowPass(!showPass)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-subtle hover:text-muted-foreground transition-colors"
            >
              {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          {form.new_password && (
            <div className="mt-2 space-y-1.5">
              <div className="flex gap-1 h-1">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className={`flex-1 transition-colors ${i < strength ? strengthColor : "bg-muted"}`} style={{ borderRadius: 1 }} />
                ))}
              </div>
              <ul className="grid grid-cols-2 gap-x-3 gap-y-0.5">
                {passRules.map((r) => (
                  <li key={r.key} className={`text-[11px] flex items-center gap-1 ${r.ok ? "text-success" : "text-subtle"}`}>
                    <span>{r.ok ? "✓" : "·"}</span>{r.label}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
            Confirm password
          </label>
          <input
            type="password"
            required
            value={form.confirm}
            onChange={(e) => setForm({ ...form, confirm: e.target.value })}
            className="field-input"
          />
          {form.confirm && form.confirm !== form.new_password && (
            <p className="text-[11px] text-error mt-1">Passwords do not match.</p>
          )}
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 justify-center">
          {loading ? "Updating…" : "Update password"}
        </button>
      </form>
    </div>
  );
}

export default ResetPasswordPage;
