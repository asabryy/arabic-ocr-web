import React from "react";
import { Link, useLocation } from "react-router-dom";

function NavLinkItem({ to, label }) {
  const location = useLocation();
  const isActive = location.pathname.startsWith(to);

  return (
    <Link
      to={to}
      className={`block px-4 py-2 rounded transition-colors duration-200 ${
        isActive
          ? "bg-secondary text-primary font-semibold"
          : "hover:bg-background-subtle dark:hover:bg-primary-light"
      }`}
    >
      {label}
    </Link>
  );
}

export default NavLinkItem;
