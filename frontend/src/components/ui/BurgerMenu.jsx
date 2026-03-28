// src/components/ui/BurgerMenu.jsx
import React, { Fragment } from "react";
import { Menu, MenuButton, MenuItems, MenuItem } from "@headlessui/react";
import { MenuIcon } from "lucide-react";
import clsx from "clsx";
import { Link } from "react-router-dom";

const BurgerMenu = ({ user, onLogout, openLogin, openRegister }) => {
  return (
    <Menu as="div" className="relative inline-block text-left z-50">
      <MenuButton
        as={Fragment}
      >
        <button
          aria-label="Open menu"
          className="p-2 rounded-md hover:bg-white/10 transition"
        >
          <MenuIcon className="w-6 h-6 text-white" />
        </button>
      </MenuButton>

      <MenuItems
        anchor="bottom end"
        className="absolute right-0 mt-2 w-48 origin-top-right bg-white text-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
      >
        {user ? (
          <>
            <div className="px-4 py-2 text-sm font-medium text-gray-600 border-b">
              Hi, {user.name}
            </div>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <Link
                  to="/dashboard"
                  className={clsx(
                    "block px-4 py-2 text-sm",
                    focus && "bg-gray-100"
                  )}
                >
                  Dashboard
                </Link>
              )}
            </MenuItem>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <Link
                  to="/settings"
                  className={clsx(
                    "block px-4 py-2 text-sm",
                    focus && "bg-gray-100"
                  )}
                >
                  Settings
                </Link>
              )}
            </MenuItem>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <Link
                  to="/support"
                  className={clsx(
                    "block px-4 py-2 text-sm",
                    focus && "bg-gray-100"
                  )}
                >
                  Support
                </Link>
              )}
            </MenuItem>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <button
                  onClick={onLogout}
                  className={clsx(
                    "w-full text-left block px-4 py-2 text-sm text-red-600",
                    focus && "bg-gray-100"
                  )}
                >
                  Logout
                </button>
              )}
            </MenuItem>
          </>
        ) : (
          <>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <button
                  onClick={openLogin}
                  className={clsx(
                    "w-full text-left block px-4 py-2 text-sm",
                    focus && "bg-gray-100"
                  )}
                >
                  Login
                </button>
              )}
            </MenuItem>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <button
                  onClick={openRegister}
                  className={clsx(
                    "w-full text-left block px-4 py-2 text-sm",
                    focus && "bg-gray-100"
                  )}
                >
                  Sign Up
                </button>
              )}
            </MenuItem>
          </>
        )}
      </MenuItems>
    </Menu>
  );
};

export default BurgerMenu;
