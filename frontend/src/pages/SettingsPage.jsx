import React, { useState } from "react";
import Button from "../components/ui/Button";
import { useAuth } from "../auth/AuthContext";
import { updateCurrentUser } from "../features/auth/authservice";

function SettingsPage() {
  const { user, login } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [email] = useState(user?.email || "");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    setStatus("");

    const token = localStorage.getItem("access_token");
    try {
      await updateCurrentUser(token, { name });
      await login(token); // refresh context with updated user
      setStatus("Changes saved successfully.");
    } catch (err) {
      console.error("Failed to update user:", err);
      setStatus("Failed to update. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const resendVerification = () => {
    // Placeholder — to be implemented later
    console.log("Resending verification email");
    setStatus("Verification email sent.");
  };

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-brand">Settings</h1>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <label className="block font-semibold mb-1">Name</label>
          <input
            type="text"
            className="w-full border border-gray-300 rounded px-3 py-2"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div>
          <label className="block font-semibold mb-1">Email</label>
          <input
            type="email"
            value={email}
            className="w-full border border-gray-200 bg-gray-100 rounded px-3 py-2"
            disabled
          />
        </div>

        {!user?.is_verified && (
          <div className="text-yellow-700 text-sm">
            Your email is not verified.{" "}
            <button onClick={resendVerification} className="underline text-blue-600">
              Resend verification email
            </button>
          </div>
        )}

        <div className="flex items-center gap-4">
          <Button variant="primary" onClick={handleSave} disabled={loading}>
            {loading ? "Saving..." : "Save Changes"}
          </Button>
          {status && <p className="text-sm text-gray-600">{status}</p>}
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
