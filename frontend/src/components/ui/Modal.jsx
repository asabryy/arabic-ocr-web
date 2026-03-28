import React from "react";

function Modal({ isOpen, onClose, children }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-background text-content dark:bg-background-dark dark:text-content-light rounded-xl shadow-xl p-6 w-full max-w-md relative">
        <button
          className="absolute top-2 right-2 text-content-muted hover:text-secondary"
          onClick={onClose}
        >
          ✕
        </button>
        {children}
      </div>
    </div>
  );
}

export default Modal;
