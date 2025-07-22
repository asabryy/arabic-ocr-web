import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { authApi } from "../api/auth";

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
        setMessage("Email verified! Redirecting to login...");
        setTimeout(() => navigate("/login"), 2000);
      } catch (err) {
        setMessage("Verification failed. The link may be invalid or expired.");
      }
    };

    verify();
  }, [location.search, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-lg">{message}</p>
    </div>
  );
}

export default VerifyEmail;