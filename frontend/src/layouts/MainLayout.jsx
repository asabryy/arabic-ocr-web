import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import TopNavbar from "../components/layout/TopNavbar";
import Sidebar from "../components/layout/Sidebar";

function MainLayout({ children, openLogin, openRegister }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    const check = () => setIsSidebarOpen(window.innerWidth >= 1024);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const handleLogout = () => { logout(); navigate("/"); };

  return (
    <div className="min-h-screen w-full bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      <TopNavbar
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        user={user}
        onLogout={handleLogout}
        openLogin={openLogin}
        openRegister={openRegister}
      />
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
      <div className={`pt-12 transition-[padding] duration-200 ease-in-out min-h-screen ${
        isSidebarOpen ? "lg:pl-52 rtl:lg:pl-0 rtl:lg:pr-52" : ""
      }`}>
        <main className="p-6 max-w-5xl mx-auto">{children}</main>
      </div>
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/20 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
    </div>
  );
}

export default MainLayout;
