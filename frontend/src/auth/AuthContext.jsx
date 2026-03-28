// src/auth/AuthContext.js
import React, { createContext, useContext, useState, useEffect } from "react";
import { getCurrentUser } from "../features/auth/authservice";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      getCurrentUser(token)
        .then((userData) => setUser(userData))
        .catch((err) => {
          console.error("Failed to fetch current user:", err);
          localStorage.removeItem("access_token");
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (token) => {
    localStorage.setItem("access_token", token);
    try {
      const userData = await getCurrentUser(token);
      setUser(userData);
    } catch (err) {
      console.error("Login failed:", err);
      logout();
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
