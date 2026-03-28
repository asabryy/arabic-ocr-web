import React from "react";
import { MenuIcon } from "lucide-react";

const NavMenu = ({ isOpen, setIsOpen }) => (
  <button
    onClick={() => setIsOpen(!isOpen)}
    className="text-content-light p-2 focus:outline-none"
    aria-label="Toggle sidebar"
  >
    <MenuIcon className="h-6 w-6" />
  </button>
);

export default NavMenu;
