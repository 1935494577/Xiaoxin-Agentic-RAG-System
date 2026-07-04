import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authLogin, authLogout, authMe } from "../api/client";
import { AUTH_SESSION_KEY } from "../lib/constants";
import { resolveAdminRole, type AdminRole } from "../lib/adminRoles";

export type AuthSession = {
  username: string;
  department: string;
  role: AdminRole;
  token: string;
  userId: string;
  displayName: string;
  loggedInAt: number;
};

type AuthContextValue = {
  userId: string;
  session: AuthSession | null;
  isAuthenticated: boolean;
  username: string;
  displayName: string;
  department: string;
  role: AdminRole;
  token: string;
  login: (username: string, password: string, remember?: boolean) => Promise<AuthSession>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readSession(storage: Storage): AuthSession | null {
  const raw = storage.getItem(AUTH_SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as AuthSession;
    if (parsed?.username && parsed?.token && parsed?.userId) {
      const displayName =
        (parsed.displayName ?? "").trim() || (parsed.username ?? "").trim();
      return {
        ...parsed,
        displayName,
        role: parsed.role ?? resolveAdminRole(parsed.department ?? ""),
      };
    }
  } catch {
    /* ignore */
  }
  return null;
}

function loadInitialSession(): AuthSession | null {
  return readSession(localStorage) ?? readSession(sessionStorage);
}

function writeSession(session: AuthSession, remember: boolean): void {
  const storage = remember ? localStorage : sessionStorage;
  const other = remember ? sessionStorage : localStorage;
  other.removeItem(AUTH_SESSION_KEY);
  storage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(loadInitialSession);

  useEffect(() => {
    if (!session?.token) return;
    const storedName = (session.displayName || "").trim();
    const username = (session.username || "").trim();
    if (storedName && storedName !== username) return;

    let cancelled = false;
    authMe()
      .then((user) => {
        if (cancelled) return;
        const nextName = (user.display_name || user.username || "").trim();
        if (!nextName || nextName === storedName) return;
        const updated: AuthSession = { ...session, displayName: nextName };
        const remember = Boolean(localStorage.getItem(AUTH_SESSION_KEY));
        writeSession(updated, remember);
        setSession(updated);
      })
      .catch(() => {
        /* offline or expired — keep cached session */
      });

    return () => {
      cancelled = true;
    };
  }, [session?.token, session?.userId, session?.displayName, session?.username]);

  const login = useCallback(async (username: string, password: string, remember = true) => {
    const res = await authLogin(username.trim(), password, remember);
    const displayName = (res.user.display_name || res.user.username || "").trim();
    const next: AuthSession = {
      username: res.user.username,
      department: res.user.department,
      role: resolveAdminRole(res.user.department),
      token: res.token,
      userId: res.user.id,
      displayName,
      loggedInAt: Date.now(),
    };
    writeSession(next, remember);
    setSession(next);
    return next;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authLogout();
    } catch {
      /* ignore network errors on logout */
    }
    localStorage.removeItem(AUTH_SESSION_KEY);
    sessionStorage.removeItem(AUTH_SESSION_KEY);
    setSession(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      userId: session?.userId ?? "",
      session,
      isAuthenticated: session !== null,
      username: session?.username ?? "",
      displayName: session?.displayName ?? "",
      department: session?.department ?? "",
      role: session?.role ?? "operator",
      token: session?.token ?? "",
      login,
      logout,
    }),
    [session, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
