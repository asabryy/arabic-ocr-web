import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

import Sidebar from "../components/layout/Sidebar";
import TopNavbar from "../components/layout/TopNavbar";

function MainLayout({ children, openLogin, openRegister }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen w-full font-sans bg-background text-content dark:bg-background-dark dark:text-content-light">
      {/* Top Navbar */}
      <TopNavbar
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        user={user}
        onLogout={handleLogout}
        openLogin={openLogin}
        openRegister={openRegister}
      />

      {/* Sidebar */}
      <Sidebar isOpen={isSidebarOpen} />

      {/* Main Content */}
      <div
        className={`pt-16 transition-all duration-300 ease-in-out
          ${isSidebarOpen ? "lg:ml-64" : "lg:ml-0"}
          min-h-[calc(100vh-4rem)] overflow-y-auto flex flex-col
        `}
      >
        <main className="flex-grow p-6">{children}</main>
        <footer className="bg-primary-dark text-content-light text-center py-4">
          <p className="text-sm">
            &copy; {new Date().getFullYear()} TextAra. All rights reserved.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default MainLayout;
