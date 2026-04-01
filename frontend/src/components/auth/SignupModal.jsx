import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { GoogleLogin } from "@react-oauth/google";
import toast from "react-hot-toast";
import { Check, X, Eye, EyeOff } from "lucide-react";
import Modal from "../ui/Modal";
import { useAuth } from "../../auth/AuthContext";
import { registerUser, googleAuth } from "../../features/auth/authservice";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const PASSWORD_RULES = [
  { key: "minLength", label: "8+ characters",          test: (p) => p.length >= 8 },
  { key: "uppercase", label: "Uppercase (A–Z)",         test: (p) => /[A-Z]/.test(p) },
  { key: "number",    label: "Number (0–9)",            test: (p) => /[0-9]/.test(p) },
  { key: "special",   label: "Special character",       test: (p) => /[^A-Za-z0-9]/.test(p) },
];

function isStrongPassword(p) { return PASSWORD_RULES.every((r) => r.test(p)); }

function PasswordStrengthMeter({ password }) {
  if (!password) return null;
  const passed = PASSWORD_RULES.filter((r) => r.test(password)).length;
  const pct = (passed / PASSWORD_RULES.length) * 100;
  const [barColor] = pct <= 25 ? ["bg-red-500"] : pct <= 50 ? ["bg-amber-500"] : pct <= 75 ? ["bg-yellow-400"] : ["bg-emerald-500"];

  return (
    <div className="mt-2 space-y-1.5">
      <div className="h-0.5 bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
        <div className={`h-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-0.5">
        {PASSWORD_RULES.map((r) => {
          const ok = r.test(password);
          return (
            <li key={r.key} className={`text-[11px] flex items-center gap-1 ${ok ? "text-emerald-600 dark:text-emerald-400" : "text-zinc-400 dark:text-zinc-500"}`}>
              {ok ? <Check className="w-3 h-3 shrink-0" /> : <div className="w-3 h-3 shrink-0 border border-current rounded-full opacity-40" />}
              {r.label}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SignupModal({ isOpen, onClose }) {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm]             = useState({ name: "", email: "", password: "", confirm: "" });
  const [touched, setTouched]       = useState({});
  const [showPassword, setShowPwd]  = useState(false);
  const [loading, setLoading]       = useState(false);
  const [registered, setRegistered] = useState(false);

  const errors = {
    name:     !form.name.trim()                 ? "Required."             : "",
    email:    !form.email.trim()                ? "Required."             :
              !EMAIL_RE.test(form.email)        ? "Invalid email."        : "",
    password: !form.password                   ? "Required."             :
              !isStrongPassword(form.password) ? "Too weak."             : "",
    confirm:  form.confirm !== form.password   ? "Passwords don't match." : "",
  };

  const isFormValid = Object.values(errors).every((e) => !e);
  const blur = (f) => setTouched((t) => ({ ...t, [f]: true }));
  const show = (f) => touched[f] && errors[f];

  const handleSubmit = async (e) => {
    e.preventDefault();
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
      onClose();
      navigate("/dashboard");
    } catch {
      toast.error("Google sign-up failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t("auth.signup.title")}>
      {registered ? (
        <div className="space-y-4 text-center">
          <div className="w-10 h-10 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center mx-auto">
            <span className="text-lg">✉️</span>
          </div>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{t("auth.signup.checkInboxTitle")}</p>
          <button onClick={onClose} className="text-sm text-indigo-500 hover:text-indigo-600 font-medium transition-colors">
            {t("auth.signup.backToSignIn")}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{t("auth.signup.subtitle")}</p>
          <form onSubmit={handleSubmit} className="space-y-3" noValidate>

            {/* Name */}
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Full name</label>
              <input type="text" autoComplete="name" value={form.name} placeholder="Your name"
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                onBlur={() => blur("name")}
                className={`field-input ${show("name") ? "border-red-400" : ""}`} />
              {show("name") && <p className="mt-1 text-xs text-red-500">{errors.name}</p>}
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Email</label>
              <div className="relative">
                <input type="email" autoComplete="email" value={form.email} placeholder="you@example.com"
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  onBlur={() => blur("email")}
                  className={`field-input pr-8 ${show("email") ? "border-red-400" : touched.email && !errors.email ? "border-emerald-400" : ""}`} />
                {touched.email && !errors.email && <Check className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-emerald-500 pointer-events-none" />}
              </div>
              {show("email") && <p className="mt-1 text-xs text-red-500">{errors.email}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Password</label>
              <div className="relative">
                <input type={showPassword ? "text" : "password"} autoComplete="new-password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  onBlur={() => blur("password")}
                  className={`field-input pr-9 ${show("password") && errors.password ? "border-red-400" : ""}`} />
                <button type="button" onClick={() => setShowPwd((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600">
                  {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
              <PasswordStrengthMeter password={form.password} />
            </div>

            {/* Confirm */}
            <div>
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Confirm password</label>
              <input type="password" autoComplete="new-password" value={form.confirm}
                onChange={(e) => setForm({ ...form, confirm: e.target.value })}
                onBlur={() => blur("confirm")}
                className={`field-input ${show("confirm") ? "border-red-400" : form.confirm && !errors.confirm ? "border-emerald-400" : ""}`} />
              {show("confirm") && <p className="mt-1 text-xs text-red-500">{errors.confirm}</p>}
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 justify-center mt-1">
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
            <Link to="/login" onClick={onClose} className="text-indigo-500 hover:text-indigo-600 font-medium transition-colors">
              {t("auth.signup.signIn")}
            </Link>
          </p>
        </div>
      )}
    </Modal>
  );
}

export default SignupModal;
