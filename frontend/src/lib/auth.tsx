import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Me } from "./api";

interface AuthCtx {
  me: Me | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
  setMe: (m: Me | null) => void;
}

const Ctx = createContext<AuthCtx>(null as any);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setMe(await api<Me>("/api/auth/me"));
    } catch {
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } finally {
      setMe(null);
    }
  }, []);

  useEffect(() => {
    refresh();
    const onUnauth = () => setMe(null);
    window.addEventListener("rimetra:unauthorized", onUnauth);
    return () => window.removeEventListener("rimetra:unauthorized", onUnauth);
  }, [refresh]);

  return <Ctx.Provider value={{ me, loading, refresh, logout, setMe }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
