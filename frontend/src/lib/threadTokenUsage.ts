import { apiGet } from "../api/client";
import type { TokenUsage } from "../lib/tokenUsage";

export type ThreadTokenUsageModelBreakdown = {
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_runs: number;
};

export type ThreadTokenUsageCallerBreakdown = {
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;
};

export type ThreadTokenUsageResponse = {
  thread_id: string;
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_runs: number;
  by_model?: Record<string, ThreadTokenUsageModelBreakdown>;
  by_caller?: ThreadTokenUsageCallerBreakdown;
};

/** One LLM chat.completions call recorded in Jnao SQLite. */
export type TokenUsageCallRecord = {
  id: string;
  created_at: string;
  session_id: string;
  user_id?: string;
  channel?: string;
  model: string;
  caller: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  question_preview: string;
};

/** Aggregated by session + question (one user turn may include multiple LLM calls). */
export type TokenUsageTurnRecord = {
  session_id: string;
  question_preview: string;
  created_at: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  llm_call_count: number;
  callers: string[];
  call_ids?: string[];
};

export type TokenUsageSummaryResponse = {
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_calls: number;
  total_runs: number;
  total_llm_calls: number;
  by_model: Record<string, ThreadTokenUsageModelBreakdown>;
  records: TokenUsageCallRecord[];
  turns?: TokenUsageTurnRecord[];
  source: string;
  available: boolean;
};

export function threadTokenUsageQueryKey(threadId?: string | null) {
  return ["thread-token-usage", threadId] as const;
}

export function tokenUsageSummaryQueryKey(limit = 100) {
  return ["token-usage-summary", limit] as const;
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
      by_model: {},
      by_caller: { total_tokens: 0, total_input_tokens: 0, total_output_tokens: 0 },
    };
  }
}

export async function fetchTokenUsageSummary(limit = 100): Promise<TokenUsageSummaryResponse> {
  try {
    return await apiGet<TokenUsageSummaryResponse>(`/api/token-usage/summary?limit=${limit}`);
  } catch {
    return {
      total_tokens: 0,
      total_input_tokens: 0,
      total_output_tokens: 0,
      total_calls: 0,
      total_runs: 0,
      total_llm_calls: 0,
      by_model: {},
      records: [],
      turns: [],
      source: "unavailable",
      available: false,
    };
  }
}

export type OpsDigestResponse = {
  since: string;
  since_days: number;
  token_usage: {
    total_tokens: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_calls: number;
  };
  feedback: {
    total: number;
    positive: number;
    negative: number;
    pending_triage: number;
    retrieval_miss: number;
  };
  generated_at: string;
};

export function opsDigestQueryKey(sinceDays = 1) {
  return ["ops-digest", sinceDays] as const;
}

export async function fetchOpsDigest(sinceDays = 1): Promise<OpsDigestResponse | null> {
  try {
    return await apiGet<OpsDigestResponse>(`/api/ops/digest?since_days=${sinceDays}`);
  } catch {
    return null;
  }
}
