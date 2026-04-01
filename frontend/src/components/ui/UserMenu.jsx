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
            "focus:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500 transition-colors",
            user
              ? "w-7 h-7 bg-indigo-500 text-white flex items-center justify-center text-xs font-bold hover:bg-indigo-600"
              : "p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
          )}
          style={{ borderRadius: 2 }}
        >
          {user ? (user.name?.[0]?.toUpperCase() || "U") : <User className="w-4 h-4" />}
        </button>
      </MenuButton>
      <MenuItems
        anchor={isRtl ? "bottom start" : "bottom end"}
        className={clsx(
          "w-52 py-1 focus:outline-none z-50",
          isRtl ? "origin-top-left" : "origin-top-right"
        )}
        style={{
          background: 'white',
          border: '1px solid rgb(228 228 231)',
          borderRadius: 2,
          boxShadow: '0 4px 24px rgba(0,0,0,0.12)',
        }}
      >
        {user ? (
          <>
            <div className="px-3 py-2.5 border-b border-zinc-100">
              <p className="text-sm font-semibold text-zinc-900 truncate">{user.name}</p>
              <p className="text-xs text-zinc-400 truncate mt-0.5">{user.email}</p>
            </div>
            <div className="p-1">
              {[
                { icon: LayoutDashboard, label: t("userMenu.dashboard"), to: "/dashboard" },
                { icon: Settings,        label: t("userMenu.settings"),  to: "/settings" },
              ].map(({ icon: Icon, label, to }) => (
                <MenuItem key={to} as={Fragment}>
                  {({ focus }) => (
                    <Link to={to}
                      className={clsx("flex items-center gap-2 px-3 py-2 text-sm transition-colors", focus ? "bg-zinc-50 text-zinc-900" : "text-zinc-600")}
                      style={{ borderRadius: 2 }}>
                      <Icon className="w-3.5 h-3.5 shrink-0" />
                      {label}
                    </Link>
                  )}
                </MenuItem>
              ))}
              <div className="my-1 border-t border-zinc-100" />
              <MenuItem as={Fragment}>
                {({ focus }) => (
                  <button onClick={onLogout}
                    className={clsx("w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors", focus ? "bg-red-50 text-red-600" : "text-red-500")}
                    style={{ borderRadius: 2 }}>
                    <LogOut className="w-3.5 h-3.5 shrink-0" />
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
                <button onClick={openLogin}
                  className={clsx("w-full text-left px-3 py-2 text-sm transition-colors", focus ? "bg-zinc-50 text-zinc-900" : "text-zinc-600")}
                  style={{ borderRadius: 2 }}>
                  {t("userMenu.signIn")}
                </button>
              )}
            </MenuItem>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <button onClick={openRegister}
                  className={clsx("w-full text-left px-3 py-2 text-sm font-medium transition-colors", focus ? "bg-indigo-50 text-indigo-600" : "text-indigo-500")}
                  style={{ borderRadius: 2 }}>
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
