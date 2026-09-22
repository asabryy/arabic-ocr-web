import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getCurrentUser } from "../features/auth/authservice";
import { onSessionExpired } from "../api/client";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Memoized: `login` used to be re-created every render, and anything holding it
  // in an effect's dependency list (BillingSuccess's payment poll) tore itself
  // down and restarted on each call, so its retry counter never advanced.
  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("access_token");
  }, []);

  const login = useCallback(
    async (newToken) => {
      localStorage.setItem("access_token", newToken);
      try {
        const userData = await getCurrentUser(newToken);
        setUser(userData);
        setToken(newToken);
        return userData;
      } catch (err) {
        // Only a genuine rejection ends the session. This used to log the user out
        // on any failure, so one flaky /users/me — including during the poll right
        // after a successful payment — dumped them on the signed-out landing page.
        const status = err?.response?.status;
        if (status === 401 || status === 403) {
          logout();
        }
        throw err;
      }
    },
    [logout]
  );

  useEffect(() => {
    const stored = localStorage.getItem("access_token");
    if (!stored) {
      setLoading(false);
      return;
    }
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
  }, []);

  // Access tokens last 30 minutes. The API client refreshes them transparently on a
  // 401 and only broadcasts here when that fails, at which point the session really
  // is over and the UI must stop pretending otherwise.
  useEffect(() => onSessionExpired(logout), [logout]);

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
