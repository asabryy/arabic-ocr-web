// src/components/layout/Sidebar.jsx
import React from "react";
import { Link } from "react-router-dom";
import Logo from "../../assets/logo.svg?react";
import NavLinkItem from "../ui/NavLinkItem";
import DarkModeToggle from "../ui/DarkModeToggle";

const Sidebar = ({ isOpen }) => {
  return (
    <aside
        className={`
            fixed top-16 left-0 z-40 h-[calc(100vh-4rem)] w-64
            bg-primary-dark text-content-light
            transform transition-transform duration-300 ease-in-out
            ${isOpen ? "translate-x-0 lg:translate-x-0" : "-translate-x-full lg:-translate-x-full"}
            flex flex-col
        `}
    >
      {/* Scrollable nav section */}
      <div className="flex-1 overflow-y-auto p-6">
        <nav className="flex flex-col space-y-4">
          <NavLinkItem to="/dashboard" label="Dashboard" />
          <NavLinkItem to="/upload" label="Convert" />
          <NavLinkItem to="/coming-soon" label="Translate" />
          <NavLinkItem to="/coming-soon" label="Authenticate" />
          <NavLinkItem to="/settings" label="Settings" />
        </nav>
      </div>

      {/* Dark mode toggle */}
      <div className="p-4 border-t border-white/20">
        <DarkModeToggle />
      </div>
    </aside>
  );
};

export default Sidebar;
