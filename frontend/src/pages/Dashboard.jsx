// src/pages/Dashboard.jsx
import React from "react";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";

function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-background py-10">
    <div className="container max-w-4xl text-center">
        <h1 className="text-3xl font-bold text-brand mb-2">
        Welcome, {user?.email}
        </h1>
        <p className="text-gray-700 mb-6">
        This is your dashboard. You can upload files, manage documents, and more.
        </p>
        <div className="flex flex-col md:flex-row justify-center items-center gap-4">
        <button
            className="bg-brand text-white px-6 py-2 rounded-xl hover:bg-brand-dark transition"
            onClick={() => navigate("/upload")}
        >
            Upload Document
        </button>
        <button
            className="bg-accent text-white px-6 py-2 rounded-xl hover:opacity-90 transition"
            onClick={() => navigate("/coming-soon")}
        >
            Other Features
        </button>
        <button
            onClick={handleLogout}
            className="bg-red-600 text-white px-6 py-2 rounded-xl hover:bg-red-700 transition"
        >
            Logout
        </button>
        </div>
    </div>
    </div>
  );
}

export default Dashboard;
