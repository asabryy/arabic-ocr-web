import React, { useState } from "react";
import Modal from "../ui/Modal";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { useAuth } from "../../auth/AuthContext";
import { loginUser } from "../../features/auth/authservice";

const LoginModal = ({ isOpen, onClose }) => {
  const { login } = useAuth();  // Only use login from context
  const [form, setForm] = useState({ email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const accessToken = await loginUser(form);   // Just get token
      await login(accessToken);                    // Let context handle storage + fetching user
      onClose();
      navigate("/dashboard");                                   
    } catch (err) {
      console.error(err);
      setError(err?.response?.data?.detail || err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Log In to TextAra">
      <form onSubmit={handleSubmit} className="space-y-4 mt-4">
        <Input
          label="Email"
          type="email"
          name="email"
          value={form.email}
          onChange={handleChange}
          required
        />
        <Input
          label="Password"
          type="password"
          name="password"
          value={form.password}
          onChange={handleChange}
          required
        />
        {error && <p className="text-red-500 text-sm">{error}</p>}

        <Button type="submit" disabled={loading} className="w-full">
          {loading ? "Logging in..." : "Login"}
        </Button>
      </form>
    </Modal>
  );
};

export default LoginModal;
