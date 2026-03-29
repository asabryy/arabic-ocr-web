import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { GoogleLogin } from "@react-oauth/google";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";
import { registerUser, googleAuth } from "../features/auth/authservice";

const passwordRules = () => [
  { key: "minLength", test: (p) => p.length >= 8 },
  { key: "uppercase", test: (p) => /[A-Z]/.test(p) },
  { key: "number", test: (p) => /[0-9]/.test(p) },
  { key: "special", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

const isValidPassword = (p) => passwordRules().every((r) => r.test(p));

function PasswordStrength({ password }) {
  const { t } = useTranslation();
  const rules = passwordRules();
  if (!password) return null;

  const passed = rules.filter((r) => r.test(password)).length;
  const pct = (passed / rules.length) * 100;
  const barColor =
    pct <= 25 ? "bg-red-500" : pct <= 50 ? "bg-amber-500" : pct <= 75 ? "bg-yellow-400" : "bg-emerald-500";

  return (
    <div className="mt-2 space-y-2">
      <div className="h-1 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-1">
        {rules.map((r) => (
          <li
            key={r.key}
            className={`text-[11px] flex items-center gap-1 ${
              r.test(password) ? "text-emerald-600 dark:text-emerald-400" : "text-zinc-400 dark:text-zinc-500"
            }`}
          >
            <span>{r.test(password) ? "✓" : "·"}</span>
            {t(`auth.password.${r.key}`)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SignupPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isValidPassword(form.password)) return;
    if (form.password !== form.confirm) {
      toast.error(t("auth.password.mismatch"));
      return;
    }
    setLoading(true);
    try {
      await registerUser({ name: form.name, email: form.email, password: form.password });
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

  if (registered) {
    return (
      <div className="text-center space-y-5">
        <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center mx-auto">
          <span className="text-2xl">✉️</span>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            {t("auth.signup.checkInboxTitle")}
          </h1>
          <p
            className="text-sm text-zinc-500 dark:text-zinc-400 mt-2 leading-relaxed"
            dangerouslySetInnerHTML={{
              __html: t("auth.signup.checkInboxBody", { email: form.email }),
            }}
          />
        </div>
        <Link
          to="/login"
          className="inline-block text-sm text-indigo-500 hover:text-indigo-600 font-medium transition-colors"
        >
          {t("auth.signup.backToSignIn")}
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{t("auth.signup.title")}</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">{t("auth.signup.subtitle")}</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            {t("auth.signup.name")}
          </label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            {t("auth.signup.email")}
          </label>
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            {t("auth.signup.password")}
          </label>
          <input
            type="password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <PasswordStrength password={form.password} />
        </div>
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            {t("auth.signup.confirmPassword")}
          </label>
          <input
            type="password"
            required
            value={form.confirm}
            onChange={(e) => setForm({ ...form, confirm: e.target.value })}
            className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 text-sm font-medium rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white transition-colors disabled:opacity-60"
        >
          {loading ? t("auth.signup.submitting") : t("auth.signup.submit")}
        </button>
      </form>
      <div className="relative flex items-center gap-3">
        <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-700" />
        <span className="text-xs text-zinc-400">{t("auth.signup.orSignUpWith")}</span>
        <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-700" />
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
