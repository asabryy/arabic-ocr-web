import React from "react";
import { useNavigate } from "react-router-dom";

function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 flex flex-col items-center justify-center text-center px-4">
      <div className="text-[9rem] font-extrabold leading-none text-zinc-100 dark:text-zinc-900 select-none tabular-nums mb-6">
        404
      </div>
      <h1 className="text-xl font-semibold mb-2">Page not found</h1>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">The page you're looking for doesn't exist.</p>
      <button onClick={() => navigate("/")} className="btn-primary px-6 py-2">Go Home</button>
    </div>
  );
}

export default NotFound;
