// src/components/ui/UserMenu.jsx
import React, { Fragment } from "react";
import { Menu, MenuButton, MenuItems, MenuItem } from "@headlessui/react";
import { MoreVertical } from "lucide-react";
import clsx from "clsx";
import { Link } from "react-router-dom";

const UserMenu = ({ user, onLogout, openLogin, openRegister }) => {
  return (
    <Menu as="div" className="relative inline-block text-left z-50">
      <MenuButton as={Fragment}>
        <button
            className={`p-2 focus:outline-none ${
            user
                ? "rounded-full bg-gray-200 text-gray-800 w-9 h-9 flex items-center justify-center"
                : "text-white"
            }`}
        >
            {user ? (
            <span className="text-sm font-medium">
                {user.name?.[0]?.toUpperCase() || "U"}
            </span>
            ) : (
            <MoreVertical className="w-5 h-5" />
            )}
        </button>
    </MenuButton>
      <MenuItems
        anchor="bottom end"
        className="absolute right-0 mt-2 w-48 origin-top-right bg-white text-gray-800 rounded shadow-lg py-1 ring-1 ring-black ring-opacity-5 focus:outline-none"
      >
        {user ? (
          <>
            <div className="px-4 py-2 text-sm border-b">Hi, {user.name}</div>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <Link
                  to="/dashboard"
                  className={clsx("block px-4 py-2 text-sm", focus && "bg-gray-100")}
                >
                  Dashboard
                </Link>
              )}
            </MenuItem>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <Link
                  to="/settings"
                  className={clsx("block px-4 py-2 text-sm", focus && "bg-gray-100")}
                >
                  Settings
                </Link>
              )}
            </MenuItem>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <button
                  onClick={onLogout}
                  className={clsx("w-full text-left block px-4 py-2 text-sm", focus && "bg-gray-100")}
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
                  className={clsx("w-full text-left block px-4 py-2 text-sm", focus && "bg-gray-100")}
                >
                  Login
                </button>
              )}
            </MenuItem>
            <MenuItem as={Fragment}>
              {({ focus }) => (
                <button
                  onClick={openRegister}
                  className={clsx("w-full text-left block px-4 py-2 text-sm", focus && "bg-gray-100")}
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

export default UserMenu;
