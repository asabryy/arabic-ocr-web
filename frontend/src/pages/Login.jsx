// src/pages/Login.jsx

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../api/auth";
import { useAuth } from "../auth/AuthContext";

function Login() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const navigate                = useNavigate();
  const { user, login }         = useAuth();

  // Redirect as soon as the context user is set
  useEffect(() => {
    console.log("ProtectedRoute/user changed:", user);
    if (user) {
      console.log("Navigating to dashboard");
      navigate("/dashboard", { replace: true });
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    console.log("Attempting login for:", email);

    // 1) Exchange credentials for a JWT at /token
    const form = new URLSearchParams();
    form.append("grant_type", "password");
    form.append("username", email);
    form.append("password", password);

    try {
      const { data: tokenRes } = await authApi.post(
        "/token",
        form,
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );
      console.log("Token response:", tokenRes);

      // 2) Fetch the authenticated user's profile
      const { data: me } = await authApi.get("/users/me", {
        headers: { Authorization: `Bearer ${tokenRes.access_token}` }
      });
      console.log("Fetched user profile:", me);

      // 3) Store user + token in context (triggers redirect)
      login(me, tokenRes.access_token);

    } catch (err) {
      console.error("Login error:", err);
      setError("Invalid credentials. Please try again.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded shadow-md w-96">
        <h2 className="text-2xl font-bold mb-6 text-center">Login</h2>
        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-4 p-2 border rounded"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-6 p-2 border rounded"
          required
        />
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700"
        >
          Sign In
        </button>
        <p className="mt-4 text-sm text-center text-gray-600">
          Don&apos;t have an account?{" "}
          <a href="/register" className="text-blue-600 hover:underline">
            Sign up
          </a>
        </p>
      </form>
    </div>
  );
}

export default Login;
