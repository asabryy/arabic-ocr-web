import React, { useState } from "react";
import { createPortal } from "react-dom";
import { registerUser } from "../../features/auth/authservice";
import Button from "../ui/Button";
import Input from "../ui/Input";

function SignupModal({ isOpen, onClose }) {
  const [formData, setFormData] = useState({ name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  if (!isOpen) return null;

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      await registerUser(formData);
      setMessage("Registration successful! Please check your email to verify.");
    } catch (error) {
      setMessage(error?.response?.data?.detail || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-lg relative">
        <button
          onClick={onClose}
          className="absolute top-3 right-4 text-gray-400 hover:text-gray-600 text-xl"
        >
          &times;
        </button>
        <h2 className="text-2xl font-bold mb-4 text-center text-brand">Sign Up</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            name="name"
            label="Name"
            type="text"
            value={formData.name}
            onChange={handleChange}
            required
          />
          <Input
            name="email"
            label="Email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            required
          />
          <Input
            name="password"
            label="Password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            required
          />

          {message && <p className="text-sm text-center text-red-600">{message}</p>}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Signing up..." : "Sign Up"}
          </Button>
        </form>
      </div>
    </div>,
    document.body
  );
}

export default SignupModal;