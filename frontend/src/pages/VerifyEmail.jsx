// src/pages/VerifyEmail.jsx
import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { authApi } from "../features/auth/authservice";

function VerifyEmail() {
  const [message, setMessage] = useState("Verifying...");
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get("token");
    if (!token) {
      setMessage("Invalid verification link.");
      return;
    }

    const verify = async () => {
      try {
        await authApi.get(`/verify-email?token=${token}`);
        setMessage("✅ Email verified! Redirecting...");
        setTimeout(() => navigate("/"), 2500);
      } catch (err) {
        setMessage("❌ Verification failed. Link may be expired.");
      }
    };

    verify();
  }, [location.search, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary">
      <div className="card text-center space-y-4">
        <h2 className="heading">Email Verification</h2>
        <p className="text-muted">{message}</p>
      </div>
    </div>
  );
}

export default VerifyEmail;
