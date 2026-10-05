import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, tokenStore } from "./api";
import type { AppUser } from "./types";

interface AuthCtx {
  user: AppUser | null;
  loading: boolean;
  /** Vrai pour le rôle ADMIN. */
  isAdmin: boolean;
  /** Teste une permission (ex. "data:write"). Indication d'interface uniquement : le backend fait foi. */
  can: (permission: string) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  /** Remplace le jeton (après un changement de mot de passe) sans déconnecter l'utilisateur. */
  adoptToken: (token: string) => Promise<void>;
}

const Ctx = createContext<AuthCtx>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStore.get()) {
      setLoading(false);
      return;
    }
    api.get<AppUser>("/auth/me").then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  const adoptToken = useCallback(async (token: string) => {
    tokenStore.set(token);
    setUser(await api.get<AppUser>("/auth/me"));
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.post<{ access_token: string }>("/auth/login", { email, password });
      await adoptToken(res.access_token);
    },
    [adoptToken],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const value = useMemo<AuthCtx>(() => {
    const perms = new Set(user?.permissions ?? []);
    return { user, loading, isAdmin: user?.role === "ADMIN", can: (p) => perms.has(p), login, logout, adoptToken };
  }, [user, loading, login, logout, adoptToken]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
