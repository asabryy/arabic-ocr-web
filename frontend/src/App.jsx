import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import AuthProvider from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";

import MainLayout from "./layouts/MainLayout";
import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";
import Upload from "./features/uploads/Uploadpage";
import NotFound from "./pages/NotFound";
import ComingSoon from "./pages/ComingSoon";
import VerifyEmail from "./pages/VerifyEmail";
import LoginModal from "./components/auth/LoginModal";
import SignupModal from "./components/auth/SignupModal";
import SettingsPage from "./pages/SettingsPage";

function App() {
  const [showLogin, setShowLogin] = useState(false);
  const [showRegister, setShowRegister] = useState(false);

  const openLogin = () => setShowLogin(true);
  const openRegister = () => setShowRegister(true);
  const closeModals = () => {
    setShowLogin(false);
    setShowRegister(false);
  };

  return (
    <AuthProvider>
      <Router>
        <MainLayout
          openLogin={openLogin}
          openRegister={openRegister}
        >
          <Routes>
            <Route path="/" element={<LandingPage openLogin={openLogin} openRegister={openRegister} />} />
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

          {/* Modals are rendered outside routing so they're always accessible */}
          {showLogin && <LoginModal isOpen onClose={closeModals} />}
          {showRegister && <SignupModal isOpen onClose={closeModals} />}
        </MainLayout>
      </Router>
    </AuthProvider>
  );
}

export default App;
