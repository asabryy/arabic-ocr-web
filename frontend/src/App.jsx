import React from "react";
import { Toaster } from "react-hot-toast";
import { GoogleOAuthProvider } from "@react-oauth/google";
import AuthProvider from "./auth/AuthContext";
import AppRoutes from "./router/Routes";

function App() {
  return (
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID || ""}>
      <AuthProvider>
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            style: {
              borderRadius: "0.75rem",
              fontSize: "0.8125rem",
              fontFamily: "Inter, ui-sans-serif, system-ui",
              padding: "10px 14px",
            },
          }}
        />
        <AppRoutes />
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
