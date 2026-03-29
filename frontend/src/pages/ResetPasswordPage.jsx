import React, { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { resetPassword } from "../features/auth/authservice";

function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [form, setForm] = useState({ new_password: "", confirm: "" });
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  if (!token) {
    return (
      <div className="text-center space-y-4">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Invalid link</h1>
        <p className="text-zinc-500 dark:text-zinc-400 text-sm">
          This password reset link is missing a token.
        </p>
        <Link
          to="/forgot-password"
          className="text-sm text-indigo-500 hover:text-indigo-600 transition-colors"
        >
          Request a new link
        </Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="text-center space-y-4">
        <div className="text-5xl">✅</div>
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Password updated</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Your password has been changed successfully.
        </p>
        <Link
          to="/login"
          className="inline-block text-sm font-medium text-indigo-500 hover:text-indigo-600 transition-colors"
        >
          Sign in
        </Link>
      </div>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
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

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Set new password</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Choose a strong password for your account.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            New password
          </label>
          <input
            type="password"
            required
            value={form.new_password}
            onChange={(e) => setForm({ ...form, new_password: e.target.value })}
            className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            Confirm password
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
          {loading ? "Updating…" : "Update password"}
        </button>
      </form>
    </div>
  );
}

export default ResetPasswordPage;
