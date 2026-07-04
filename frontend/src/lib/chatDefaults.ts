import type { UiConfig } from "../api/types";

/** Server UI config is the source of truth for chat behavior (LAN-wide consistency). */
export function resolveStreamFastMode(
  uiConfig: Pick<UiConfig, "stream_fast_mode"> | null | undefined
): boolean | undefined {
  if (typeof uiConfig?.stream_fast_mode === "boolean") {
    return uiConfig.stream_fast_mode;
  }
  return undefined;
}
