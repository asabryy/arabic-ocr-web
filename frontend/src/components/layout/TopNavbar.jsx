import React from "react";
import { Link } from "react-router-dom";
import { Menu } from "lucide-react";
import Logo from "../../assets/Logo.jsx";
import UserMenu from "../ui/UserMenu";
import LanguageToggle from "../ui/LanguageToggle";
import DarkModeToggle from "../ui/DarkModeToggle";

const TopNavbar = ({ isSidebarOpen, setIsSidebarOpen, user, onLogout, openLogin, openRegister }) => {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-12 bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800">
      <nav className="flex items-center h-full px-4 gap-2">
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
          aria-label="Toggle sidebar"
        >
          <Menu className="h-4 w-4" />
        </button>
        <Link to="/" className="flex items-center gap-2 ml-2 shrink-0">
          <Logo className="h-4 w-auto fill-zinc-900 dark:fill-white" />
        </Link>
        <div className="flex-1" />
        <div className="flex items-center gap-1 shrink-0">
          <div className="hidden lg:flex items-center gap-1">
            <LanguageToggle />
            <DarkModeToggle />
          </div>
          <UserMenu
            user={user}
            onLogout={onLogout}
            openLogin={openLogin}
            openRegister={openRegister}
          />
        </div>
      </nav>
    </header>
  );
};

export default TopNavbar;
