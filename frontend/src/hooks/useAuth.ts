import { useMemo, useState } from "react";
import { USER_ID_KEY } from "../lib/constants";

function loadOrCreateUserId(): string {
  const raw = localStorage.getItem(USER_ID_KEY);
  if (raw) {
    // Handle both plain string (old code) and JSON-wrapped (useLocalStorage) formats
    try { return JSON.parse(raw) as string; } catch { return raw; }
  }
  const id = `u_${Math.random().toString(36).slice(2, 14)}`;
  localStorage.setItem(USER_ID_KEY, id);
  return id;
}

export function useAuth() {
  const [userId] = useState(loadOrCreateUserId);
  return useMemo(() => ({ userId }), [userId]);
}
