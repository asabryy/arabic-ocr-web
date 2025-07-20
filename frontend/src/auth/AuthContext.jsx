
import React, { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const rawUser  = localStorage.getItem("user");
    const rawToken = localStorage.getItem("token");

    // Only attempt to parse if there’s actually something valid stored
    if (rawUser && rawToken && rawUser !== "undefined") {
      try {
        const parsed = JSON.parse(rawUser);
        setUser(parsed);
      } catch (err) {
        console.error("Failed to parse stored user:", err);
        // Clean up the bad data so it doesn’t keep breaking
        localStorage.removeItem("user");
        localStorage.removeItem("token");
      }
    }
  }, []);

  const login = (userData, token) => {
    // Persist user info and token
    setUser(userData);
    localStorage.setItem("user", JSON.stringify(userData));
    localStorage.setItem("token", token);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("user");
    localStorage.removeItem("token");
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export default AuthProvider;