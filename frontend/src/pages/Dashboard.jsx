import React from "react";
import { Link } from "react-router-dom";
import Button from "../components/ui/Button";

function Dashboard() {
  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-brand">Your Dashboard</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Documents</h2>
        {/* Replace this with mapped document list later */}
        <p className="text-gray-600">No documents uploaded yet.</p>
        <Link to="/upload">
          <Button className="mt-4" variant="primary">
            Upload New Document
          </Button>
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Account Summary</h2>
        <ul className="text-gray-700 space-y-1">
          <li><strong>Plan:</strong> Free</li>
          <li><strong>Pages Used:</strong> 0 / 50</li>
          <li><strong>Next Reset:</strong> August 31, 2025</li>
        </ul>
      </div>
    </div>
  );
}

export default Dashboard;
