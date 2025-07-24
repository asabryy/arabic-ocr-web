// src/layouts/MainLayout.jsx
import React from "react";
import { Link } from "react-router-dom";

function MainLayout({ children }) {
  return (
    <div className="min-h-screen bg-background text-brand-dark font-sans">
      <header className="bg-brand text-onBrand shadow">
        <nav className="container flex justify-between items-center py-4">
          <Link to="/" className="text-2xl font-bold">
            TextAra
          </Link>
          <div className="space-x-4">
            <Link to="/login" className="hover:underline text-onBrand">Login</Link>
            <Link to="/register" className="hover:underline text-onBrand">Sign Up</Link>
          </div>
        </nav>
      </header>

      <main className="container py-8">{children}</main>

      <footer className="bg-brand-dark text-onBrand text-center py-4 mt-12">
        <p className="text-sm">&copy; {new Date().getFullYear()} TextAra. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default MainLayout;
