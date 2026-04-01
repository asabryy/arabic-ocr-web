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
        [
          "flex items-center gap-2.5 px-3 py-2 text-[13px] font-medium transition-colors relative",
          isActive
            ? "text-indigo-600 dark:text-indigo-400 bg-indigo-50/80 dark:bg-indigo-500/8 border-l-2 border-indigo-500 dark:border-indigo-400 pl-[10px]"
            : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 border-l-2 border-transparent pl-[10px] hover:bg-zinc-50 dark:hover:bg-zinc-800/50",
        ].join(" ")
      }
    >
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span className="flex-1">{label}</span>
      {badge && (
        <span className="text-[9px] font-semibold tracking-widest uppercase text-zinc-400 dark:text-zinc-600">
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
        fixed top-12 left-0 rtl:left-auto rtl:right-0 z-40
        h-[calc(100vh-3rem)] w-52
        bg-white dark:bg-zinc-950
        border-r rtl:border-r-0 rtl:border-l border-zinc-200 dark:border-zinc-800
        transform transition-transform duration-200 ease-in-out
        flex flex-col
        ${isOpen ? "translate-x-0" : "-translate-x-full rtl:translate-x-full"}
      `}
    >
      {/* Section: Main nav */}
      <div className="flex-1 overflow-y-auto py-4">
        <p className="section-label px-4 mb-3">Navigation</p>
        <div className="flex flex-col">
          <NavItem to="/dashboard"   label={t("sidebar.dashboard")}    icon={LayoutDashboard} />
          <NavItem to="/convert"     label={t("sidebar.convert")}      icon={FileOutput} />
          <NavItem to="/coming-soon" label={t("sidebar.translate")}    icon={Languages}  badge="Soon" />
          <NavItem to="/coming-soon" label={t("sidebar.authenticate")} icon={ShieldCheck} badge="Soon" />
        </div>

        <div className="mx-4 my-4 border-t border-zinc-100 dark:border-zinc-800" />

        <p className="section-label px-4 mb-3">Account</p>
        <div className="flex flex-col">
          <NavItem to="/pricing"  label={t("sidebar.pricing")}  icon={Tag} />
          <NavItem to="/settings" label={t("sidebar.settings")} icon={Settings} />
        </div>
      </div>

      {/* Bottom */}
      <div className="px-4 py-3 border-t border-zinc-100 dark:border-zinc-800 space-y-2">
        <div className="flex items-center gap-1 lg:hidden">
          <LanguageToggle />
          <DarkModeToggle />
        </div>
        <p className="section-label">© {new Date().getFullYear()} Textara</p>
      </div>
    </aside>
  );
};

export default Sidebar;
