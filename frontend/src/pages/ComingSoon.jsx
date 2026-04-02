import React from "react";
import { Link } from "react-router-dom";

function ComingSoon() {
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 flex flex-col items-center justify-center text-center px-4">
      <div className="text-[7rem] font-extrabold leading-none text-zinc-100 dark:text-zinc-900 select-none mb-6">
        Soon
      </div>
      <h1 className="text-xl font-semibold mb-2">Coming Soon</h1>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-xs leading-relaxed mb-8">
        We're working on this feature. Stay tuned for updates.
      </p>
      <Link to="/dashboard" className="btn-secondary px-6 py-2">Back to Dashboard</Link>
    </div>
  );
}

export default ComingSoon;
