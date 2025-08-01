import React, { useState } from "react";
import { BrowserRouter as Router } from "react-router-dom";
import AuthProvider from "./auth/AuthContext";

import MainLayout from "./layouts/MainLayout";
import AppRoutes from "./router/Routes";

import LoginModal from "./components/auth/LoginModal";
import SignupModal from "./components/auth/SignupModal";

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
        <MainLayout openLogin={openLogin} openRegister={openRegister}>
          <AppRoutes openLogin={openLogin} openRegister={openRegister} />
          {showLogin && <LoginModal isOpen onClose={closeModals} />}
          {showRegister && <SignupModal isOpen onClose={closeModals} />}
        </MainLayout>
      </Router>
    </AuthProvider>
  );
}

export default App;
