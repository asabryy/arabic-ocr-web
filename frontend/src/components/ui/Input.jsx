import React from "react";

const Input = ({ label, ...props }) => (
  <div className="mb-4">
    {label && <label className="block text-sm font-medium mb-1">{label}</label>}
    <input
      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
      {...props}
    />
  </div>
);

export default Input;
