import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokens } from "@/lib/api";

type AuthResult = { user: any; landingRoute?: string | null };

type AuthState = {
  user: any | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<AuthResult>;
  signup: (payload: any) => Promise<AuthResult>;
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
      return null;
    }
    try {
      const { data } = await api.get("/v2/auth/me");
      setUser(data);
      return data;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const login = async (email: string, password: string): Promise<AuthResult> => {
    const { data } = await api.post("/v2/auth/login", { email, password });
    tokens.set(data.access_token, data.refresh_token);
    const currentUser = await loadMe();
    return { user: currentUser || data.user, landingRoute: data.landing_route };
  };

  const signup = async (payload: any): Promise<AuthResult> => {
    const accountType = String(payload?.account_type || "user").toLowerCase();
    const { account_type: _accountType, ...signupPayload } = payload || {};
    const endpoint =
      accountType === "creator"
        ? "/v2/auth/signup/creator"
        : accountType === "coin_trader"
          ? "/v2/auth/signup/trader"
          : "/v2/auth/signup/user";
    const { data } = await api.post(endpoint, signupPayload);
    if (data.access_token) tokens.set(data.access_token, data.refresh_token);
    else {
      const res = await api.post("/v2/auth/login", { email: signupPayload.email, password: signupPayload.password });
      tokens.set(res.data.access_token, res.data.refresh_token);
    }
    const currentUser = await loadMe();
    return { user: currentUser || data.user, landingRoute: data.landing_route };
  };

  const logout = () => {
    api.post("/v2/auth/logout").catch(() => undefined);
    tokens.clear();
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, signup, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
