// src/components/ui/NavMenu.jsx
import React, { useState } from "react";
import { Link } from "react-router-dom";
import { MenuIcon, X } from "lucide-react";

const NavMenu = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Button to toggle drawer */}
      <button
        onClick={() => setIsOpen(true)}
        className="text-white p-2 focus:outline-none"
        aria-label="Open navigation menu"
      >
        <MenuIcon className="h-6 w-6" />
      </button>

      {/* Slide-out drawer */}
      <div
        className={`fixed top-0 left-0 h-full w-64 bg-white text-gray-800 shadow-lg transform transition-transform duration-300 z-50 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Close button */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h2 className="text-lg font-bold">Navigation</h2>
          <button onClick={() => setIsOpen(false)} aria-label="Close menu">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex flex-col space-y-4 px-4 py-6">
          <Link to="/translate" onClick={() => setIsOpen(false)}>Document Translation</Link>
          <Link to="/about" onClick={() => setIsOpen(false)}>About</Link>
          <Link to="/blog" onClick={() => setIsOpen(false)}>Blog</Link>
          <Link to="/contact" onClick={() => setIsOpen(false)}>Contact</Link>
        </nav>
      </div>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-30 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
};

export default NavMenu;
