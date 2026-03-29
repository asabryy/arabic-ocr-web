import React, { Fragment } from "react";
import { Menu, MenuButton, MenuItems, MenuItem } from "@headlessui/react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { User, LayoutDashboard, Settings, LogOut } from "lucide-react";
import clsx from "clsx";

const UserMenu = ({ user, onLogout, openLogin, openRegister }) => {
  const { t, i18n } = useTranslation();
  const isRtl = i18n.language === "ar";

  return (
    <Menu as="div" className="relative inline-block text-left z-50">
      <MenuButton as={Fragment}>
        <button
          className={clsx(
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-zinc-950",
            user
              ? "w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-white flex items-center justify-center text-sm font-semibold hover:opacity-90 transition-opacity"
              : "p-2 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          )}
        >
          {user ? (
            (user.name?.[0]?.toUpperCase()) || "U"
          ) : (
            <User className="w-4 h-4" />
          )}
        </button>
      </MenuButton>
      <MenuItems
        anchor={isRtl ? "bottom start" : "bottom end"}
        className={clsx(
          "w-52 glass-card rounded-xl shadow-xl shadow-black/10 dark:shadow-black/40 py-1 focus:outline-none z-50",
          isRtl ? "origin-top-left" : "origin-top-right"
        )}
      >
        {user ? (
          <>
            <div className="px-4 py-3 border-b border-zinc-100 dark:border-zinc-800">
              <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">{user.name}</p>
              <p className="text-xs text-zinc-400 dark:text-zinc-500 truncate mt-0.5">{user.email}</p>
            </div>
            <div className="p-1">
              <MenuItem as={Fragment}>
                {({ focus }) => (
                  <Link
                    to="/dashboard"
                    className={clsx(
                      "flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-colors",
                      "text-zinc-600 dark:text-zinc-300",
                      focus && "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                    )}
                  >
                    <LayoutDashboard className="w-4 h-4 shrink-0" />
                    {t("userMenu.dashboard")}
                  </Link>
                )}
              </MenuItem>
              <MenuItem as={Fragment}>
                {({ focus }) => (
                  <Link
                    to="/settings"
                    className={clsx(
                      "flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-colors",
                      "text-zinc-600 dark:text-zinc-300",
                      focus && "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                    )}
                  >
                    <Settings className="w-4 h-4 shrink-0" />
                    {t("userMenu.settings")}
                  </Link>
                )}
              </MenuItem>
              <div className="my-1 border-t border-zinc-100 dark:border-zinc-800" />
              <MenuItem as={Fragment}>
                {({ focus }) => (
                  <button
                    onClick={onLogout}
                    className={clsx(
                      "w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-colors",
                      "text-red-500 dark:text-red-400",
                      focus && "bg-red-50 dark:bg-red-500/10"
                    )}
                  >
                    <LogOut className="w-4 h-4 shrink-0" />
                    {t("userMenu.signOut")}
                  </button>
                )}
              </MenuItem>
            </div>
          </>
        ) : (
          <div className="p-1">
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <button
                  onClick={openLogin}
                  className={clsx(
                    "w-full text-left px-3 py-2 text-sm rounded-lg transition-colors",
                    "text-zinc-600 dark:text-zinc-300",
                    focus && "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                  )}
                >
                  {t("userMenu.signIn")}
                </button>
              )}
            </MenuItem>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <button
                  onClick={openRegister}
                  className={clsx(
                    "w-full text-left px-3 py-2 text-sm rounded-lg transition-colors",
                    "text-zinc-600 dark:text-zinc-300",
                    focus && "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                  )}
                >
                  {t("userMenu.createAccount")}
                </button>
              )}
            </MenuItem>
          </div>
        )}
      </MenuItems>
    </Menu>
  );
};

export default UserMenu;
