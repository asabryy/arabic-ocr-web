import React from "react";
import { Link } from "react-router-dom";
import Logo from "../assets/Logo.jsx";
import DarkModeToggle from "../components/ui/DarkModeToggle";
import LanguageToggle from "../components/ui/LanguageToggle";

function AuthLayout({ children }) {
  return (
    <div className="min-h-screen flex bg-white dark:bg-zinc-950">

      {/* ── Left panel: brand / illustration ── */}
      <div className="hidden lg:flex flex-col w-[44%] bg-zinc-950 dark:bg-zinc-900 relative overflow-hidden">
        {/* Subtle grid texture */}
        <div className="absolute inset-0 [background-image:linear-gradient(rgba(99,102,241,0.04)_1px,transparent_1px),linear-gradient(to_right,rgba(99,102,241,0.04)_1px,transparent_1px)] [background-size:40px_40px]" />
        <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-transparent to-zinc-950/60" />

        {/* Logo */}
        <div className="relative z-10 p-8">
          <Link to="/">
            <Logo className="h-5 w-auto fill-white opacity-90" />
          </Link>
        </div>

        {/* Center content */}
        <div className="relative z-10 flex-1 flex flex-col justify-center px-10 pb-16">
          <div className="space-y-6">
            {/* Large accent number */}
            <div className="text-[7rem] font-extrabold leading-none text-white/5 select-none tabular-nums">
              OCR
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white leading-tight mb-3">
                Arabic documents,<br />instantly converted.
              </h2>
              <p className="text-sm text-zinc-400 leading-relaxed max-w-xs">
                Upload a scanned Arabic PDF and receive a fully editable Word document in seconds.
              </p>
            </div>
            {/* Mini feature list */}
            <ul className="space-y-2">
              {["RTL-accurate text extraction", "GPU-powered processing", "Cloud storage included"].map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-xs text-zinc-400">
                  <div className="w-1 h-1 bg-indigo-500 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom mark */}
        <div className="relative z-10 px-10 py-6 border-t border-zinc-800">
          <p className="text-xs text-zinc-600">© {new Date().getFullYear()} Textara</p>
        </div>
      </div>

      {/* ── Right panel: form ── */}
      <div className="flex-1 flex flex-col">
        {/* Top bar */}
        <header className="flex items-center justify-between px-6 h-12 border-b border-zinc-200 dark:border-zinc-800">
          <Link to="/" className="lg:hidden">
            <Logo className="h-4 w-auto fill-zinc-900 dark:fill-white" />
          </Link>
          <div className="lg:hidden flex-1" />
          <div className="flex items-center gap-1 ml-auto">
            <LanguageToggle />
            <DarkModeToggle />
          </div>
        </header>

        {/* Form area */}
        <main className="flex-1 flex items-center justify-center px-6 py-10">
          <div className="w-full max-w-sm animate-slide-up">
            {children}
          </div>
        </main>

        <footer className="px-6 py-4 border-t border-zinc-100 dark:border-zinc-800 text-center">
          <p className="text-xs text-zinc-400 dark:text-zinc-600">© {new Date().getFullYear()} Textara</p>
        </footer>
      </div>
    </div>
  );
}

export default AuthLayout;
