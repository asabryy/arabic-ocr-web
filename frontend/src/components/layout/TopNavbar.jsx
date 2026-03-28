// src/components/layout/TopNavbar.jsx
import React from "react";
import { Link } from "react-router-dom";
import Logo from "../../assets/logo.svg?react";
import NavMenu from "../ui/NavMenu";
import UserMenu from "../ui/UserMenu";

const TopNavbar = ({ isSidebarOpen, setIsSidebarOpen, user, onLogout, openLogin, openRegister }) => {
  return (
    <header className="sticky top-0 z-50 bg-primary text-content-light shadow h-16 w-full">
      <nav className="flex justify-between items-center h-full px-6">
        {/* Left: Toggle + Logo */}
        <div className="flex items-center gap-4">
          <NavMenu isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />
          <Link to="/">
            <Logo className="h-6 w-auto fill-white" />
          </Link>
        </div>

        {/* Right: User */}
        <UserMenu
          user={user}
          onLogout={onLogout}
          openLogin={openLogin}
          openRegister={openRegister}
        />
      </nav>
    </header>
  );
};

export default TopNavbar;
