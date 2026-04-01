import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { GoogleLogin } from "@react-oauth/google";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";
import { loginUser, googleAuth } from "../features/auth/authservice";

function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const token = await loginUser(form);
      await login(token);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Incorrect email or password.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async ({ credential }) => {
    setLoading(true);
    try {
      const token = await googleAuth(credential);
      await login(token);
      navigate("/dashboard", { replace: true });
    } catch {
      toast.error("Google sign-in failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("auth.login.title")}</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">{t("auth.login.subtitle")}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1.5">
            {t("auth.login.email")}
          </label>
          <input type="email" required value={form.email} placeholder="you@example.com"
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="field-input" />
        </div>
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
              {t("auth.login.password")}
            </label>
            <Link to="/forgot-password" className="text-xs text-indigo-500 hover:text-indigo-600 transition-colors">
              {t("auth.login.forgotPassword")}
            </Link>
          </div>
          <input type="password" required value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="field-input" />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 justify-center">
          {loading ? t("auth.login.submitting") : t("auth.login.submit")}
        </button>
      </form>

      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
        <span className="text-xs text-zinc-400">{t("auth.signup.orContinueWith")}</span>
        <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
      </div>

      <div className="flex justify-center">
        <GoogleLogin onSuccess={handleGoogle} onError={() => toast.error("Google sign-in failed.")} />
      </div>

      <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
        {t("auth.login.noAccount")}{" "}
        <Link to="/signup" className="text-indigo-500 hover:text-indigo-600 font-medium transition-colors">
          {t("auth.login.createOne")}
        </Link>
      </p>
    </div>
  );
}

export default LoginPage;
