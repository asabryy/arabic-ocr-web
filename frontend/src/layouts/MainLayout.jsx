import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

import Logo from "../assets/logo.svg?react";
import NavMenu from "../components/ui/NavMenu";
import UserMenu from "../components/ui/UserMenu";

function MainLayout({ children, openLogin, openRegister }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background text-brand-dark font-sans">
      {/* Header */}
      <header className="bg-brand text-onBrand shadow">
        <nav className="container flex justify-between items-center py-4">
          {/* Left: Drawer menu + Logo */}
          <div className="flex items-center gap-4">
            <NavMenu />
            <Link to="/">
              <Logo className="h-10 w-auto fill-white" />
            </Link>
          </div>

          {/* Right: User menu */}
          <UserMenu
            user={user}
            onLogout={handleLogout}
            openLogin={openLogin}
            openRegister={openRegister}
          />
        </nav>
      </header>

      {/* Main content */}
      <main className="container py-8">{children}</main>

      {/* Footer */}
      <footer className="bg-brand-dark text-onBrand text-center py-4 mt-12">
        <p className="text-sm">
          &copy; {new Date().getFullYear()} TextAra. All rights reserved.
        </p>
      </footer>
    </div>
  );
}

export default MainLayout;
