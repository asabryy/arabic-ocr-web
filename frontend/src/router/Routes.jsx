import React, { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

import MainLayout from "../layouts/MainLayout";
import AuthLayout from "../layouts/AuthLayout";
import LoginModal from "../components/auth/LoginModal";
import SignupModal from "../components/auth/SignupModal";

import LandingPage from "../pages/LandingPage";
import Dashboard from "../pages/Dashboard";
import ConvertPage from "../pages/ConvertPage";
import Upload from "../features/uploads/Uploadpage";
import LoginPage from "../pages/LoginPage";
import SignupPage from "../pages/SignupPage";
import ForgotPasswordPage from "../pages/ForgotPasswordPage";
import ResetPasswordPage from "../pages/ResetPasswordPage";
import VerifyEmail from "../pages/VerifyEmail";
import SettingsPage from "../pages/SettingsPage";
import PricingPage from "../pages/PricingPage";
import ComingSoon from "../pages/ComingSoon";
import NotFound from "../pages/NotFound";

const AUTH_ONLY_PATHS = ["/login", "/signup", "/forgot-password", "/reset-password"];
const PUBLIC_PATHS = ["/pricing", "/coming-soon"];

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? children : <Navigate to="/" replace />;
}

function RouterContent() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [showLogin, setShowLogin] = useState(false);
  const [showRegister, setShowRegister] = useState(false);

  const openLogin = () => setShowLogin(true);
  const openRegister = () => setShowRegister(true);
  const closeModals = () => { setShowLogin(false); setShowRegister(false); };

  const isAuthPage = AUTH_ONLY_PATHS.some((p) => pathname.startsWith(p));
  const isLanding = pathname === "/" && !user;
  const isPublicPage = !user && PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  const routes = (
    <Routes>
      <Route
        path="/"
        element={
          user
            ? <Navigate to="/dashboard" replace />
            : <LandingPage openLogin={openLogin} openRegister={openRegister} />
        }
      />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/convert" element={<ProtectedRoute><ConvertPage /></ProtectedRoute>} />
      <Route path="/upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="/pricing" element={<PricingPage openLogin={openLogin} openRegister={openRegister} />} />
      <Route path="/coming-soon" element={<ComingSoon />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );

  let content;
  if (isLanding || isPublicPage) {
    content = routes;
  } else if (isAuthPage) {
    content = <AuthLayout>{routes}</AuthLayout>;
  } else {
    content = (
      <MainLayout openLogin={openLogin} openRegister={openRegister}>
        {routes}
      </MainLayout>
    );
  }

  return (
    <>
      {content}
      {showLogin && <LoginModal isOpen onClose={closeModals} />}
      {showRegister && <SignupModal isOpen onClose={closeModals} />}
    </>
  );
}

const AppRoutes = () => {
  return (
    <BrowserRouter>
      <RouterContent />
    </BrowserRouter>
  );
};

export default AppRoutes;
