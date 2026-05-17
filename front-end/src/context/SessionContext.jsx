import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
} from "react";
import { api, clearTabAuthToken } from "../api/client";

const SessionContext = createContext(null);

/** Avoid replacing `user` when /api/me/ returns the same fields — prevents effect loops. */
function sameSessionUser(a, b) {
  if (a === b) return true;
  if (!a || !b) return false;
  return (
    a.id === b.id &&
    a.email === b.email &&
    a.username === b.username &&
    a.role === b.role &&
    String(a.profile_photo ?? "") === String(b.profile_photo ?? "")
  );
}

export function SessionProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const refreshSession = useCallback(async (opts = {}) => {
    const quiet = Boolean(opts.quiet);
    if (!quiet) {
      setLoading(true);
    }
    try {
      const { data } = await api.get("/api/me/");
      if (data.authenticated && data.user) {
        setUser((prev) =>
          sameSessionUser(prev, data.user) ? prev : data.user
        );
        setAuthenticated(true);
      } else {
        clearTabAuthToken();
        setUser(null);
        setAuthenticated(false);
      }
    } catch {
      setUser(null);
      setAuthenticated(false);
    } finally {
      if (!quiet) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  const clearSession = useCallback(() => {
    clearTabAuthToken();
    setUser(null);
    setAuthenticated(false);
  }, []);

  const value = useMemo(
    () => ({
      user,
      authenticated,
      loading,
      refreshSession,
      clearSession,
    }),
    [user, authenticated, loading, refreshSession, clearSession]
  );

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (ctx == null) {
    throw new Error("useSession must be used within SessionProvider");
  }
  return ctx;
}
