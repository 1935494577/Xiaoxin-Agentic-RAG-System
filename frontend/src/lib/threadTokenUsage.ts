import { apiGet } from "../api/client";
import type { TokenUsage } from "../lib/tokenUsage";

export type ThreadTokenUsageResponse = {
  thread_id: string;
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_runs: number;
};

export function threadTokenUsageQueryKey(threadId?: string | null) {
  return ["thread-token-usage", threadId] as const;
}

export function threadTokenUsageToTokenUsage(
  usage: ThreadTokenUsageResponse | null | undefined,
): TokenUsage | null {
  if (!usage) return null;
  return {
    inputTokens: usage.total_input_tokens ?? 0,
    outputTokens: usage.total_output_tokens ?? 0,
    totalTokens: usage.total_tokens ?? 0,
  };
}

export async function fetchThreadTokenUsage(threadId: string): Promise<ThreadTokenUsageResponse> {
  try {
    return await apiGet<ThreadTokenUsageResponse>(
      `/api/threads/${encodeURIComponent(threadId)}/token-usage`,
    );
  } catch {
    return {
      thread_id: threadId,
      total_tokens: 0,
      total_input_tokens: 0,
      total_output_tokens: 0,
      total_runs: 0,
    };
  }
}
