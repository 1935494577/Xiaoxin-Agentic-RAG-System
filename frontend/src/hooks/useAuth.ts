import { useCallback, useMemo, useState } from "react";
import { AUTH_SESSION_KEY, USER_ID_KEY } from "../lib/constants";

export type AuthSession = {
  username: string;
  department: string;
  loggedInAt: number;
};

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
    if (parsed?.username) return parsed;
  } catch {
    /* ignore */
  }
  return null;
}

function loadInitialSession(): AuthSession | null {
  return readSession(localStorage) ?? readSession(sessionStorage);
}

export function useAuth() {
  const [userId] = useState(loadOrCreateUserId);
  const [session, setSession] = useState<AuthSession | null>(loadInitialSession);

  const login = useCallback((username: string, department: string, remember = true) => {
    const next: AuthSession = {
      username: username.trim(),
      department,
      loggedInAt: Date.now(),
    };
    const storage = remember ? localStorage : sessionStorage;
    const other = remember ? sessionStorage : localStorage;
    other.removeItem(AUTH_SESSION_KEY);
    storage.setItem(AUTH_SESSION_KEY, JSON.stringify(next));
    setSession(next);
    return next;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_SESSION_KEY);
    sessionStorage.removeItem(AUTH_SESSION_KEY);
    setSession(null);
  }, []);

  return useMemo(
    () => ({
      userId,
      session,
      isAuthenticated: session !== null,
      username: session?.username ?? "",
      department: session?.department ?? "",
      login,
      logout,
    }),
    [userId, session, login, logout]
  );
}
