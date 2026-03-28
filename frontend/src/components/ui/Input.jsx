import React from "react";

const Input = ({ label, ...props }) => (
  <div className="mb-4">
    {label && (
      <label className="block text-sm font-medium text-content dark:text-content-light mb-1">
        {label}
      </label>
    )}
    <input
      className="w-full border border-content-muted dark:border-content-dark bg-background dark:bg-background-dark text-content dark:text-content-light rounded-lg px-3 py-2 placeholder-content-muted focus:outline-none focus:ring-2 focus:ring-secondary focus:border-secondary transition duration-200"
      {...props}
    />
  </div>
);

export default Input;
