import React, { useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard,
  FileOutput,
  Languages,
  ShieldCheck,
  Tag,
  Settings,
} from "lucide-react";
import LanguageToggle from "../ui/LanguageToggle";
import DarkModeToggle from "../ui/DarkModeToggle";

function NavItem({ to, label, icon: Icon, badge }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? "bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400"
            : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800"
        }`
      }
    >
      <Icon className="w-4 h-4 shrink-0" />
      <span className="flex-1">{label}</span>
      {badge && (
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
          {badge}
        </span>
      )}
    </NavLink>
  );
}

const Sidebar = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  useEffect(() => {
    if (window.innerWidth < 1024) onClose?.();
  }, [pathname]);

  return (
    <aside
      className={`
        fixed top-14 left-0 rtl:left-auto rtl:right-0 z-40 h-[calc(100vh-3.5rem)] w-60
        bg-white dark:bg-zinc-950
        border-r rtl:border-r-0 rtl:border-l border-zinc-200/80 dark:border-zinc-800/80
        transform transition-transform duration-300 ease-in-out
        flex flex-col
        ${isOpen ? "translate-x-0" : "-translate-x-full rtl:translate-x-full"}
      `}
    >
      <div className="flex-1 overflow-y-auto p-3">
        <div className="flex flex-col gap-0.5">
          <NavItem to="/dashboard" label={t("sidebar.dashboard")} icon={LayoutDashboard} />
          <NavItem to="/convert" label={t("sidebar.convert")} icon={FileOutput} />
          <NavItem to="/coming-soon" label={t("sidebar.translate")} icon={Languages} badge="Soon" />
          <NavItem to="/coming-soon" label={t("sidebar.authenticate")} icon={ShieldCheck} badge="Soon" />
        </div>
        <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800/80 flex flex-col gap-0.5">
          <NavItem to="/pricing" label={t("sidebar.pricing")} icon={Tag} />
          <NavItem to="/settings" label={t("sidebar.settings")} icon={Settings} />
        </div>
      </div>
      <div className="p-3 border-t border-zinc-100 dark:border-zinc-800/80 space-y-2">
        <div className="flex items-center gap-1 lg:hidden">
          <LanguageToggle />
          <DarkModeToggle />
        </div>
        <p className="text-[11px] text-zinc-400 dark:text-zinc-600 text-center">
          © {new Date().getFullYear()} Textara
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;
