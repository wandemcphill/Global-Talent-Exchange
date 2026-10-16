import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokens } from "@/lib/api";

type AuthState = {
  user: any | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (payload: any) => Promise<void>;
  logout: () => void;
};

const Ctx = createContext<AuthState>(null as any);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    if (!tokens.get()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const login = async (email: string, password: string) => {
    const { data } = await api.post("/auth/login", { email, password });
    tokens.set(data.access_token, data.refresh_token);
    await loadMe();
  };

  const signup = async (payload: any) => {
    const { data } = await api.post("/auth/signup/user", payload);
    if (data.access_token) tokens.set(data.access_token, data.refresh_token);
    else {
      const res = await api.post("/auth/login", { email: payload.email, password: payload.password });
      tokens.set(res.data.access_token, res.data.refresh_token);
    }
    await loadMe();
  };

  const logout = () => {
    api.post("/auth/logout").catch(() => undefined);
    tokens.clear();
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, signup, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
