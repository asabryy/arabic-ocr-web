import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { GoogleLogin } from "@react-oauth/google";
import toast from "react-hot-toast";
import Modal from "../ui/Modal";
import { useAuth } from "../../auth/AuthContext";
import { registerUser, googleAuth } from "../../features/auth/authservice";

function SignupModal({ isOpen, onClose }) {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
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
        <div className="text-center space-y-4">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {t("auth.signup.checkInboxTitle")}
          </p>
          <button
            onClick={onClose}
            className="text-sm text-indigo-500 hover:text-indigo-600 font-medium transition-colors"
          >
            {t("auth.signup.backToSignIn")}
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{t("auth.signup.subtitle")}</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: "name", type: "text", label: t("auth.signup.name") },
              { key: "email", type: "email", label: t("auth.signup.email") },
              { key: "password", type: "password", label: t("auth.signup.password") },
              { key: "confirm", type: "password", label: t("auth.signup.confirmPassword") },
            ].map(({ key, type, label }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
                  {label}
                </label>
                <input
                  type={type}
                  required
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            ))}
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
            <Link
              to="/login"
              onClick={onClose}
              className="text-indigo-500 hover:text-indigo-600 font-medium transition-colors"
            >
              {t("auth.signup.signIn")}
            </Link>
          </p>
        </div>
      )}
    </Modal>
  );
}

export default SignupModal;
