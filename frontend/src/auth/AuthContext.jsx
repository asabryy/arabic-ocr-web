import React, { createContext, useContext, useState, useEffect } from "react";
import { getCurrentUser } from "../features/auth/authservice";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("access_token");
    if (stored) {
      getCurrentUser(stored)
        .then((userData) => {
          setUser(userData);
          setToken(stored);
        })
        .catch(() => {
          localStorage.removeItem("access_token");
          setUser(null);
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (newToken) => {
    localStorage.setItem("access_token", newToken);
    try {
      const userData = await getCurrentUser(newToken);
      setUser(userData);
      setToken(newToken);
    } catch {
      logout();
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("access_token");
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export default AuthProvider;
