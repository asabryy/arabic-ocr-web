import React from "react";
import { Link } from "react-router-dom";
import Logo from "../assets/Logo.jsx";
import DarkModeToggle from "../components/ui/DarkModeToggle";
import LanguageToggle from "../components/ui/LanguageToggle";

function AuthLayout({ children }) {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex flex-col">
      <header className="flex items-center justify-between px-6 h-14">
        <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <Logo className="h-6 w-auto fill-zinc-900 dark:fill-white" />
        </Link>
        <div className="flex items-center gap-1">
          <LanguageToggle />
          <DarkModeToggle />
        </div>
      </header>
      <main className="flex-1 flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-sm">
          <div className="glass-card rounded-2xl shadow-sm shadow-black/5 dark:shadow-none p-8">
            {children}
          </div>
        </div>
      </main>
      <footer className="text-center py-5 text-xs text-zinc-400 dark:text-zinc-600">
        © {new Date().getFullYear()} Textara
      </footer>
    </div>
  );
}

export default AuthLayout;
