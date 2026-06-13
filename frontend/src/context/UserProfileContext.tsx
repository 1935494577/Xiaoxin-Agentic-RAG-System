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
import { USER_DEPT_KEY } from "../lib/constants";

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
  const { userId } = useAuth();
  const queryClient = useQueryClient();
  const [migrated, setMigrated] = useState(false);

  const { data: profile, isLoading } = useQuery({
    queryKey: ["userProfile", userId],
    queryFn: () => fetchUserProfile(userId),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!profile || migrated) return;
    const legacyDept = localStorage.getItem(USER_DEPT_KEY);
    if (legacyDept) {
      try {
        const parsed = JSON.parse(legacyDept) as string;
        if (parsed && parsed !== profile.department) {
          saveUserProfile({ user_id: userId, department: parsed })
            .then((next) => {
              queryClient.setQueryData(["userProfile", userId], next);
            })
            .catch(() => {});
        }
      } catch {
        if (legacyDept !== profile.department) {
          saveUserProfile({ user_id: userId, department: legacyDept })
            .then((next) => {
              queryClient.setQueryData(["userProfile", userId], next);
            })
            .catch(() => {});
        }
      }
    }
    setMigrated(true);
  }, [profile, migrated, userId, queryClient]);

  const saveProfile = useCallback(
    async (patch: Omit<UserProfileUpdate, "user_id">) => {
      const next = await saveUserProfile({ user_id: userId, ...patch });
      queryClient.setQueryData(["userProfile", userId], next);
      return next;
    },
    [userId, queryClient]
  );

  const value = useMemo<Ctx>(
    () => ({
      profile: profile ?? null,
      loading: isLoading,
      department: profile?.department ?? "技术部",
      displayName: profile?.display_name ?? "",
      avatarUrl: profile?.avatar_url ?? "",
      aiDisplayName: profile?.ai_display_name ?? "",
      aiAvatarUrl: profile?.ai_avatar_url ?? "",
      saveProfile,
    }),
    [profile, isLoading, saveProfile]
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
