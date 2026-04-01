import React, { useEffect, useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import { authApi } from "../features/auth/authservice";

function VerifyEmail() {
  const [status, setStatus] = useState("pending"); // pending | success | error
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get("token");
    if (!token) {
      setStatus("error");
      return;
    }
    const verify = async () => {
      try {
        await authApi.get(`/verify-email?token=${token}`);
        setStatus("success");
        setTimeout(() => navigate("/login"), 2500);
      } catch {
        setStatus("error");
      }
    };
    verify();
  }, [location.search, navigate]);

  return (
    <div className="text-center space-y-5">
      {status === "pending" && (
        <>
          <Loader2 className="w-10 h-10 text-accent animate-spin mx-auto" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Verifying your email</h1>
            <p className="text-sm text-muted-foreground mt-1">Please wait a moment…</p>
          </div>
        </>
      )}
      {status === "success" && (
        <>
          <div className="w-12 h-12 bg-success-subtle flex items-center justify-center mx-auto" style={{ borderRadius: 2 }}>
            <CheckCircle className="w-6 h-6 text-success" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Email verified</h1>
            <p className="text-sm text-muted-foreground mt-1">Redirecting you to sign in…</p>
          </div>
        </>
      )}
      {status === "error" && (
        <>
          <div className="w-12 h-12 bg-error-subtle flex items-center justify-center mx-auto" style={{ borderRadius: 2 }}>
            <XCircle className="w-6 h-6 text-error" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Verification failed</h1>
            <p className="text-sm text-muted-foreground mt-1">
              The link may be invalid or expired.
            </p>
          </div>
          <Link to="/login" className="inline-block text-sm font-medium text-accent hover:text-accent-hover transition-colors">
            Back to sign in
          </Link>
        </>
      )}
    </div>
  );
}

export default VerifyEmail;
