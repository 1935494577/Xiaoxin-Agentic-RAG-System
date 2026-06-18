import type { UiConfig } from "../api/types";

/** Server UI config is the source of truth for chat behavior (LAN-wide consistency). */
export function resolveHybridExpertMode(
  uiConfig: Pick<UiConfig, "hybrid_expert_mode"> | null | undefined,
  sessionOverride: boolean | null | undefined
): boolean {
  if (typeof sessionOverride === "boolean") return sessionOverride;
  return uiConfig?.hybrid_expert_mode ?? false;
}

export function resolveStreamFastMode(
  uiConfig: Pick<UiConfig, "stream_fast_mode"> | null | undefined
): boolean | undefined {
  if (typeof uiConfig?.stream_fast_mode === "boolean") {
    return uiConfig.stream_fast_mode;
  }
  return undefined;
}
