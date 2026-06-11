import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createSession,
  deleteSession,
  listSessions,
  loadMessages,
} from "../api/client";
import type { ChatMessage } from "../api/types";

export function useSessions(userId: string) {
  const queryClient = useQueryClient();
  const sessionsKey = ["sessions", userId];

  const { data: sessions = [], isLoading, refetch } = useQuery({
    queryKey: sessionsKey,
    queryFn: () => listSessions(userId),
  });

  const create = useCallback(async () => {
    const s = await createSession(userId);
    await refetch();
    return s;
  }, [userId, refetch]);

  const remove = useCallback(
    async (sessionId: string) => {
      await deleteSession(userId, sessionId);
      await refetch();
      queryClient.removeQueries({ queryKey: ["messages", userId, sessionId] });
    },
    [userId, refetch, queryClient]
  );

  return { sessions, isLoading, create, remove, refetch };
}

export function useMessages(userId: string, sessionId: string | null) {
  return useQuery({
    queryKey: ["messages", userId, sessionId],
    queryFn: () =>
      sessionId ? loadMessages(userId, sessionId) : Promise.resolve([] as ChatMessage[]),
    enabled: !!sessionId,
  });
}
