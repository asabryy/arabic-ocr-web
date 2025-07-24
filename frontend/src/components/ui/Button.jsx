import React from "react";
import clsx from "clsx";

const Button = ({ children, variant = "primary", className = "", ...props }) => {
  const base = "px-4 py-2 rounded-xl font-semibold transition duration-200";

  const variants = {
    primary: "bg-brand text-accent hover:bg-brand-dark",
    secondary: "bg-white border border-brand text-brand hover:bg-brand-light",
    outline: "border border-brand text-brand hover:bg-brand hover:text-accent",
    danger: "bg-red-600 text-white hover:bg-red-700"
  };

  return (
    <button className={clsx(base, variants[variant], className)} {...props}>
      {children}
    </button>
  );
};

export default Button;
