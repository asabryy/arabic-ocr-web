import React, { createContext, useContext, useState, useEffect } from "react";
import { getCurrentUser } from "../features/auth/authservice";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // Add loading state

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      getCurrentUser(token)
        .then((userData) => {
          setUser(userData);
        })
        .catch((err) => {
          console.error("Failed to fetch current user:", err);
          localStorage.removeItem("access_token");
          setUser(null);
        })
        .finally(() => {
          setLoading(false); // Stop loading whether successful or not
        });
    } else {
      setLoading(false); // No token = done loading
    }
  }, []);

  const login = async (token) => {
    localStorage.setItem("access_token", token);
    try {
      const userData = await getCurrentUser(token);
      setUser(userData);
    } catch (err) {
      console.error("Login failed to load user data:", err);
      logout(); // Clean up token on failure
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("access_token");
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export default AuthProvider;
