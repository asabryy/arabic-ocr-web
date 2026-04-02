import React from "react";
import clsx from "clsx";

const Button = ({ children, variant = "primary", className = "", ...props }) => {
  const variants = {
    primary:   "btn-primary",
    secondary: "btn-secondary",
    outline:   "btn-secondary",
    danger:    "btn-danger",
    unstyled:  "",
  };

  return (
    <button className={clsx(variants[variant], className)} {...props}>
      {children}
    </button>
  );
};

export default Button;
