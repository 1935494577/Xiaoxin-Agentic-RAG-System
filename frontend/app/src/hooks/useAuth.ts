import { useMemo } from "react";
import { USER_ID_KEY } from "../lib/constants";
import { useLocalStorage } from "./useLocalStorage";

function generateId() {
  return `u_${Math.random().toString(36).slice(2, 14)}`;
}

export function useAuth() {
  const [userId] = useLocalStorage<string>(USER_ID_KEY, generateId());
  return useMemo(() => ({ userId }), [userId]);
}
