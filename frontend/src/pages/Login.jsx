import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../features/auth/authservice";
import { useAuth } from "../auth/AuthContext";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";

function Login() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const navigate                = useNavigate();
  const { user, login }         = useAuth();

  useEffect(() => {
    if (user) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const form = new URLSearchParams();
    form.append("grant_type", "password");
    form.append("username", email);
    form.append("password", password);

    try {
      const { data: tokenRes } = await authApi.post("/token", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
      });

      const { data: me } = await authApi.get("/users/me", {
        headers: { Authorization: `Bearer ${tokenRes.access_token}` }
      });

      login(me, tokenRes.access_token);
    } catch (err) {
      setError("Invalid credentials. Please try again.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-md bg-white shadow-xl rounded-xl p-8">
        <h2 className="text-2xl font-bold text-center mb-6 text-brand">Sign in to TextAra</h2>

        {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <Button type="submit" className="w-full mt-4">Login</Button>

        <p className="text-sm text-center text-gray-600 mt-4">
          Don’t have an account?{" "}
          <a href="/register" className="text-brand hover:underline font-medium">Register</a>
        </p>
      </form>
    </div>
  );
}

export default Login;
