import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchUserProfile, saveUserProfile } from "../api/client";
import type { UserProfile, UserProfileUpdate } from "../api/types";
import { useAuth } from "../hooks/useAuth";
import { resolveEffectiveDepartment } from "../lib/departmentAccess";

type Ctx = {
  profile: UserProfile | null;
  loading: boolean;
  department: string;
  displayName: string;
  avatarUrl: string;
  aiDisplayName: string;
  aiAvatarUrl: string;
  saveProfile: (patch: Omit<UserProfileUpdate, "user_id">) => Promise<UserProfile>;
};

const UserProfileContext = createContext<Ctx | null>(null);

export function UserProfileProvider({ children }: { children: ReactNode }) {
  const { userId, isAuthenticated, department: authDepartment, updateDepartment } = useAuth();
  const queryClient = useQueryClient();
  const [syncedAuthDept, setSyncedAuthDept] = useState(false);

  const { data: profile, isLoading } = useQuery({
    queryKey: ["userProfile", userId],
    queryFn: () => fetchUserProfile(userId),
    staleTime: 60_000,
  });

  useEffect(() => {
    setSyncedAuthDept(false);
  }, [userId, authDepartment]);

  useEffect(() => {
    if (syncedAuthDept || !isAuthenticated || !authDepartment.trim() || !profile) return;
    if (profile.department === authDepartment) {
      setSyncedAuthDept(true);
      return;
    }
    saveUserProfile({ user_id: userId, department: authDepartment })
      .then((next) => {
        queryClient.setQueryData(["userProfile", userId], next);
      })
      .catch(() => {})
      .finally(() => {
        setSyncedAuthDept(true);
      });
  }, [syncedAuthDept, isAuthenticated, authDepartment, profile, userId, queryClient]);

  const saveProfile = useCallback(
    async (patch: Omit<UserProfileUpdate, "user_id">) => {
      const next = await saveUserProfile({ user_id: userId, ...patch });
      queryClient.setQueryData(["userProfile", userId], next);
      if (patch.department?.trim()) {
        updateDepartment(patch.department.trim());
      }
      return next;
    },
    [userId, queryClient, updateDepartment]
  );

  const effectiveDepartment = resolveEffectiveDepartment(
    authDepartment,
    profile?.department ?? "",
    isAuthenticated
  );

  const value = useMemo<Ctx>(
    () => ({
      profile: profile ?? null,
      loading: isLoading,
      department: effectiveDepartment,
      displayName: profile?.display_name ?? "",
      avatarUrl: profile?.avatar_url ?? "",
      aiDisplayName: profile?.ai_display_name ?? "",
      aiAvatarUrl: profile?.ai_avatar_url ?? "",
      saveProfile,
    }),
    [profile, isLoading, effectiveDepartment, saveProfile]
  );

  return <UserProfileContext.Provider value={value}>{children}</UserProfileContext.Provider>;
}

export function useUserProfile() {
  const ctx = useContext(UserProfileContext);
  if (!ctx) {
    throw new Error("useUserProfile must be used within UserProfileProvider");
  }
  return ctx;
}
