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
        <div className="w-12 h-12 bg-accent-subtle flex items-center justify-center mx-auto" style={{ borderRadius: 2 }}>
          <Mail className="w-6 h-6 text-accent" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Check your inbox</h1>
          <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
            If <span className="font-medium text-foreground">{email}</span> is registered,
            we sent a password reset link. Check your spam folder if you don't see it.
          </p>
        </div>
        <Link to="/login" className="inline-block text-sm text-accent hover:text-accent-hover font-medium transition-colors">
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Forgot password?</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Enter your email and we'll send you a reset link.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
            Email
          </label>
          <input
            type="email"
            required
            value={email}
            placeholder="you@example.com"
            onChange={(e) => setEmail(e.target.value)}
            className="field-input"
          />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 justify-center">
          {loading ? "Sending…" : "Send reset link"}
        </button>
      </form>
      <p className="text-center">
        <Link to="/login" className="text-sm text-accent hover:text-accent-hover font-medium transition-colors">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}

export default ForgotPasswordPage;
