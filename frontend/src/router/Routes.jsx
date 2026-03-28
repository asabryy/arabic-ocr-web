import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

import LandingPage from "../pages/LandingPage";
import Dashboard from "../pages/Dashboard";
import Upload from "../features/uploads/Uploadpage";
import NotFound from "../pages/NotFound";
import ComingSoon from "../pages/ComingSoon";
import VerifyEmail from "../pages/VerifyEmail";
import SettingsPage from "../pages/SettingsPage";
import ProtectedRoute from "../auth/ProtectedRoute";

const AppRoutes = ({ openLogin, openRegister }) => {
  const { user } = useAuth();

  return (
    <Routes>
      {/* 👇 Default route logic */}
      <Route
        path="/"
        element={
          user ? <Navigate to="/dashboard" replace /> : <LandingPage openLogin={openLogin} openRegister={openRegister} />
        }
      />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/upload"
        element={
          <ProtectedRoute>
            <Upload />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      <Route path="/coming-soon" element={<ComingSoon />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};

export default AppRoutes;
