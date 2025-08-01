import React from "react";
import { Link } from "react-router-dom";
import Button from "../components/ui/Button";
import FileExplorer from "../components/dashboard/FileExplorer";

function Dashboard() {
  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-content">Your Dashboard</h1>

      <div className="bg-background dark:bg-primary-light text-content dark:text-content-light rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Your Documents</h2>
        <FileExplorer onSelect={(filename) => console.log("Selected file:", filename)} />

        <Link to="/upload">
          <Button className="mt-4" variant="primary">
            Upload New Document
          </Button>
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Account Summary</h2>
        <ul className="text-content space-y-1">
          <li><strong>Plan:</strong> Free</li>
          <li><strong>Pages Used:</strong> 0 / 50</li>
          <li><strong>Next Reset:</strong> August 31, 2025</li>
        </ul>
      </div>
    </div>
  );
}

export default Dashboard;
