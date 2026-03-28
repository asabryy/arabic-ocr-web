// src/pages/PricingPage.jsx
import React from "react";

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-secondary p-6 flex flex-col items-center text-center">
      <h1 className="heading mb-4">Choose Your Plan</h1>
      <p className="text-muted mb-10 max-w-xl">
        Whether you’re an occasional user or a document-heavy pro, TextAra has a plan for you.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl w-full">
        {/* Free Plan */}
        <div className="card">
          <h2 className="text-xl font-bold mb-2 text-primary">Free</h2>
          <p className="text-muted mb-4">Perfect for light use</p>
          <ul className="list-disc list-inside text-left mb-4 text-gray-700 space-y-1">
            <li>5 pages per PDF</li>
            <li>Basic layout detection</li>
            <li>Community support</li>
          </ul>
          <p className="text-2xl font-bold mb-4">$0</p>
          <a href="/register" className="btn-primary w-full block text-center">Get Started</a>
        </div>

        {/* Pro Plan */}
        <div className="card border-2 border-primary">
          <h2 className="text-xl font-bold mb-2 text-primary">Pro</h2>
          <p className="text-muted mb-4">Ideal for frequent users</p>
          <ul className="list-disc list-inside text-left mb-4 text-gray-700 space-y-1">
            <li>50+ pages per PDF</li>
            <li>Advanced layout detection</li>
            <li>Priority processing</li>
            <li>Translation support (Coming Soon)</li>
          </ul>
          <p className="text-2xl font-bold mb-4">$9.99 / month</p>
          <a href="/coming-soon" className="btn-secondary w-full block text-center">Upgrade</a>
        </div>
      </div>
    </div>
  );
}
