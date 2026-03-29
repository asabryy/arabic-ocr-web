import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Mail } from "lucide-react";
import toast from "react-hot-toast";
import { forgotPassword } from "../features/auth/authservice";

function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch {
      toast.error("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="text-center space-y-5">
        <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center mx-auto">
          <Mail className="w-7 h-7 text-indigo-500 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Check your inbox</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2 leading-relaxed">
            If <span className="font-medium text-zinc-700 dark:text-zinc-300">{email}</span> is registered,
            we sent a password reset link. Check your spam folder if you don't see it.
          </p>
        </div>
        <Link
          to="/login"
          className="inline-block text-sm text-indigo-500 hover:text-indigo-600 font-medium transition-colors"
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Forgot password?</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Enter your email and we'll send you a reset link.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            Email
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 text-sm font-medium rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white transition-colors disabled:opacity-60"
        >
          {loading ? "Sending…" : "Send reset link"}
        </button>
      </form>
      <p className="text-center">
        <Link
          to="/login"
          className="text-sm text-indigo-500 hover:text-indigo-600 font-medium transition-colors"
        >
          Back to sign in
        </Link>
      </p>
    </div>
  );
}

export default ForgotPasswordPage;
