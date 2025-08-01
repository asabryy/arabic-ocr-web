import React from "react";
import clsx from "clsx";

const Button = ({ children, variant = "primary", className = "", ...props }) => {
  const base =
    "px-4 py-2 font-semibold transition duration-200 rounded-md focus:outline-none focus:ring-2";

  const variants = {
    primary:
      "bg-secondary text-white hover:bg-secondary-dark focus:ring-secondary",
    secondary:
      "border border-secondary text-secondary hover:bg-secondary hover:text-white focus:ring-secondary",
    outline:
      "border border-content-muted text-content-muted hover:bg-background-subtle dark:hover:bg-primary-light hover:text-secondary focus:ring-secondary",
    danger:
      "bg-red-600 text-white hover:bg-red-700 focus:ring-red-400",
    unstyled: "",
  };

  return (
    <button className={clsx(base, variants[variant], className)} {...props}>
      {children}
    </button>
  );
};

export default Button;
