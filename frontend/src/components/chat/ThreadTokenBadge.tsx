import { useQuery } from "@tanstack/react-query";
import { fetchThreadTokenUsage, threadTokenUsageQueryKey, threadTokenUsageToTokenUsage } from "../../lib/threadTokenUsage";
import { formatTokenCount, hasNonZeroUsage } from "../../lib/tokenUsage";

type Props = {
  threadId?: string | null;
};

export function ThreadTokenBadge({ threadId }: Props) {
  const { data } = useQuery({
    queryKey: threadTokenUsageQueryKey(threadId),
    queryFn: () => fetchThreadTokenUsage(threadId!),
    enabled: Boolean(threadId),
    staleTime: 15_000,
  });

  const usage = threadTokenUsageToTokenUsage(data);
  if (!hasNonZeroUsage(usage)) return null;

  return (
    <span
      className="rounded-md bg-surface-muted px-2 py-0.5 text-[11px] text-text-muted"
      title={`输入 ${usage.inputTokens} · 输出 ${usage.outputTokens}`}
    >
      Token {formatTokenCount(usage.totalTokens)}
    </span>
  );
}
