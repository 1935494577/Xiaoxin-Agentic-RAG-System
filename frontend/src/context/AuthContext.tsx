import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { AUTH_SESSION_KEY, USER_ID_KEY } from "../lib/constants";
import { resolveAdminRole, type AdminRole } from "../lib/adminRoles";

export type AuthSession = {
  username: string;
  department: string;
  role: AdminRole;
  loggedInAt: number;
};

type AuthContextValue = {
  userId: string;
  session: AuthSession | null;
  isAuthenticated: boolean;
  username: string;
  department: string;
  role: AdminRole;
  login: (username: string, department: string, remember?: boolean) => AuthSession;
  updateDepartment: (department: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function loadOrCreateUserId(): string {
  const raw = localStorage.getItem(USER_ID_KEY);
  if (raw) {
    try {
      return JSON.parse(raw) as string;
    } catch {
      return raw;
    }
  }
  const id = `u_${Math.random().toString(36).slice(2, 14)}`;
  localStorage.setItem(USER_ID_KEY, id);
  return id;
}

function readSession(storage: Storage): AuthSession | null {
  const raw = storage.getItem(AUTH_SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as AuthSession;
    if (parsed?.username) {
      return {
        ...parsed,
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

function writeSession(session: AuthSession): void {
  if (localStorage.getItem(AUTH_SESSION_KEY)) {
    localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
    return;
  }
  if (sessionStorage.getItem(AUTH_SESSION_KEY)) {
    sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
    return;
  }
  localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [userId] = useState(loadOrCreateUserId);
  const [session, setSession] = useState<AuthSession | null>(loadInitialSession);

  const login = useCallback((username: string, department: string, remember = true) => {
    const next: AuthSession = {
      username: username.trim(),
      department,
      role: resolveAdminRole(department),
      loggedInAt: Date.now(),
    };
    const storage = remember ? localStorage : sessionStorage;
    const other = remember ? sessionStorage : localStorage;
    other.removeItem(AUTH_SESSION_KEY);
    storage.setItem(AUTH_SESSION_KEY, JSON.stringify(next));
    setSession(next);
    return next;
  }, []);

  const updateDepartment = useCallback((department: string) => {
    setSession((prev) => {
      if (!prev) return prev;
      const next: AuthSession = {
        ...prev,
        department: department.trim(),
        role: resolveAdminRole(department),
      };
      writeSession(next);
      return next;
    });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_SESSION_KEY);
    sessionStorage.removeItem(AUTH_SESSION_KEY);
    setSession(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      userId,
      session,
      isAuthenticated: session !== null,
      username: session?.username ?? "",
      department: session?.department ?? "",
      role: session?.role ?? "admin",
      login,
      updateDepartment,
      logout,
    }),
    [userId, session, login, updateDepartment, logout]
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
