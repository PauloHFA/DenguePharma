import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { Role, Session } from "./roles";

interface AuthValue {
  session: Session | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

// Token só em memória do processo da aba (sessionStorage): some ao fechar a aba.
const STORAGE_KEY = "dp.session";

function load(): Session | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export class LoginError extends Error {}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(load);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (res.status === 401) throw new LoginError("E-mail ou senha inválidos.");
    if (!res.ok) throw new LoginError("Serviço indisponível. Tente novamente.");
    const { token } = (await res.json()) as { token: string };

    const me = await fetch("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } });
    if (!me.ok) throw new LoginError("Não foi possível carregar o perfil.");
    const profile = (await me.json()) as { email: string; roles: Role[] };

    const next: Session = { token, email: profile.email, roles: profile.roles };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSession(next);
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }, []);

  const value = useMemo(() => ({ session, login, logout }), [session, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fora do AuthProvider");
  return ctx;
}

