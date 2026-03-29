import React, { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import clsx from "clsx";

const DarkModeToggle = ({ className }) => {
  const [isDark, setIsDark] = useState(() => {
    const theme = localStorage.getItem("theme");
    return theme ? theme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      root.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [isDark]);

  return (
    <button
      onClick={() => setIsDark(!isDark)}
      className={clsx(
        "p-2 rounded-lg transition-colors",
        "text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200",
        "hover:bg-zinc-100 dark:hover:bg-zinc-800",
        className
      )}
      aria-label="Toggle dark mode"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
};

export default DarkModeToggle;
