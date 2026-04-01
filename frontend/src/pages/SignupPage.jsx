import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { GoogleLogin } from "@react-oauth/google";
import toast from "react-hot-toast";
import { Check, X, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { registerUser, googleAuth } from "../features/auth/authservice";

// ── Validation rules ────────────────────────────────────────────────────────

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const PASSWORD_RULES = [
  { key: "minLength", label: "At least 8 characters",           test: (p) => p.length >= 8 },
  { key: "uppercase", label: "One uppercase letter (A–Z)",      test: (p) => /[A-Z]/.test(p) },
  { key: "number",    label: "One number (0–9)",                test: (p) => /[0-9]/.test(p) },
  { key: "special",   label: "One special character (!@#…)",    test: (p) => /[^A-Za-z0-9]/.test(p) },
];

function isStrongPassword(p) { return PASSWORD_RULES.every((r) => r.test(p)); }

// ── Sub-components ──────────────────────────────────────────────────────────

function FieldError({ msg }) {
  if (!msg) return null;
  return <p className="mt-1 text-xs text-red-500 flex items-center gap-1"><X className="w-3 h-3 shrink-0" />{msg}</p>;
}

function PasswordStrengthMeter({ password }) {
  if (!password) return null;
  const passed = PASSWORD_RULES.filter((r) => r.test(password)).length;
  const pct    = (passed / PASSWORD_RULES.length) * 100;

  const [barColor, label] =
    pct <= 25  ? ["bg-red-500",    "Weak"]       :
    pct <= 50  ? ["bg-amber-500",  "Fair"]       :
    pct <= 75  ? ["bg-yellow-400", "Good"]       :
                 ["bg-emerald-500","Strong"];

  return (
    <div className="mt-2 space-y-2">
      {/* Bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-0.5 bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
          <div className={`h-full transition-all duration-300 ${barColor}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="text-[10px] font-semibold" style={{ color: pct === 100 ? "#10b981" : undefined }}>{label}</span>
      </div>
      {/* Rule checklist */}
      <ul className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        {PASSWORD_RULES.map((r) => {
          const ok = r.test(password);
          return (
            <li key={r.key} className={`text-[11px] flex items-center gap-1.5 transition-colors ${ok ? "text-emerald-600 dark:text-emerald-400" : "text-zinc-400 dark:text-zinc-500"}`}>
              {ok
                ? <Check className="w-3 h-3 shrink-0" />
                : <div className="w-3 h-3 shrink-0 border border-current rounded-full opacity-40" />
              }
              {r.label}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

function SignupPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [touched, setTouched] = useState({});           // which fields have been blurred
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm,  setShowConfirm]  = useState(false);
  const [loading,      setLoading]      = useState(false);
  const [registered,   setRegistered]   = useState(false);

  // ── Inline validation ───────────────────────────────────────────────────

  const errors = {
    name:     !form.name.trim()                        ? "Name is required."         : "",
    email:    !form.email.trim()                       ? "Email is required."        :
              !EMAIL_RE.test(form.email)               ? "Enter a valid email address." : "",
    password: !form.password                           ? "Password is required."     :
              !isStrongPassword(form.password)         ? "Password doesn't meet all requirements." : "",
    confirm:  !form.confirm                            ? "Please confirm your password." :
              form.confirm !== form.password           ? "Passwords don't match."    : "",
  };

  const isFormValid = Object.values(errors).every((e) => !e);

  const blur  = (field) => setTouched((t) => ({ ...t, [field]: true }));
  const show  = (field) => touched[field] && errors[field];

  // ── Handlers ────────────────────────────────────────────────────────────

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Mark all fields touched so errors show on submit
    setTouched({ name: true, email: true, password: true, confirm: true });
    if (!isFormValid) return;

    setLoading(true);
    try {
      await registerUser({ name: form.name.trim(), email: form.email.trim().toLowerCase(), password: form.password });
      setRegistered(true);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async ({ credential }) => {
    setLoading(true);
    try {
      const token = await googleAuth(credential);
      await login(token);
      navigate("/dashboard");
    } catch {
      toast.error("Google sign-up failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // ── Success screen ───────────────────────────────────────────────────────

  if (registered) {
    return (
      <div className="space-y-5">
        <div className="w-10 h-10 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center">
          <span className="text-lg">✉️</span>
        </div>
        <div>
          <h1 className="text-xl font-bold">{t("auth.signup.checkInboxTitle")}</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: t("auth.signup.checkInboxBody", { email: form.email }) }} />
        </div>
        <Link to="/login" className="inline-block text-sm text-indigo-500 hover:text-indigo-600 font-medium transition-colors">
          {t("auth.signup.backToSignIn")}
        </Link>
      </div>
    );
  }

  // ── Form ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("auth.signup.title")}</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">{t("auth.signup.subtitle")}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>

        {/* Name */}
        <div>
          <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
            Full name
          </label>
          <input
            type="text"
            autoComplete="name"
            value={form.name}
            placeholder="Your full name"
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            onBlur={() => blur("name")}
            className={`field-input ${show("name") ? "border-red-400 dark:border-red-500 focus:border-red-400" : ""}`}
          />
          <FieldError msg={show("name") ? errors.name : ""} />
        </div>

        {/* Email */}
        <div>
          <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
            Email address
          </label>
          <div className="relative">
            <input
              type="email"
              autoComplete="email"
              value={form.email}
              placeholder="you@example.com"
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              onBlur={() => blur("email")}
              className={`field-input pr-8 ${show("email") ? "border-red-400 dark:border-red-500 focus:border-red-400" : touched.email && !errors.email ? "border-emerald-400 dark:border-emerald-500" : ""}`}
            />
            {touched.email && !errors.email && (
              <Check className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-emerald-500 pointer-events-none" />
            )}
          </div>
          <FieldError msg={show("email") ? errors.email : ""} />
        </div>

        {/* Password */}
        <div>
          <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
            Password
          </label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              onBlur={() => blur("password")}
              className={`field-input pr-9 ${show("password") && errors.password ? "border-red-400 dark:border-red-500" : ""}`}
            />
            <button type="button" onClick={() => setShowPassword((v) => !v)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors">
              {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
          {/* Always show strength meter when typing */}
          <PasswordStrengthMeter password={form.password} />
          <FieldError msg={show("password") && errors.password ? errors.password : ""} />
        </div>

        {/* Confirm password */}
        <div>
          <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
            Confirm password
          </label>
          <div className="relative">
            <input
              type={showConfirm ? "text" : "password"}
              autoComplete="new-password"
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
              onBlur={() => blur("confirm")}
              className={`field-input pr-9 ${show("confirm") && errors.confirm ? "border-red-400 dark:border-red-500" : form.confirm && !errors.confirm ? "border-emerald-400 dark:border-emerald-500" : ""}`}
            />
            <button type="button" onClick={() => setShowConfirm((v) => !v)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors">
              {showConfirm ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
          <FieldError msg={show("confirm") ? errors.confirm : ""} />
        </div>

        {/* Terms note */}
        <p className="text-[11px] text-zinc-400 dark:text-zinc-600 leading-relaxed">
          By creating an account you agree to our{" "}
          <span className="text-zinc-500 dark:text-zinc-400">Terms of Service</span> and{" "}
          <span className="text-zinc-500 dark:text-zinc-400">Privacy Policy</span>.
        </p>

        <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 justify-center">
          {loading ? t("auth.signup.submitting") : t("auth.signup.submit")}
        </button>
      </form>

      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
        <span className="text-xs text-zinc-400">{t("auth.signup.orSignUpWith")}</span>
        <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
      </div>

      <div className="flex justify-center">
        <GoogleLogin onSuccess={handleGoogle} onError={() => toast.error("Google sign-up failed.")} />
      </div>

      <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
        {t("auth.signup.hasAccount")}{" "}
        <Link to="/login" className="text-indigo-500 hover:text-indigo-600 font-medium transition-colors">
          {t("auth.signup.signIn")}
        </Link>
      </p>
    </div>
  );
}

export default SignupPage;
