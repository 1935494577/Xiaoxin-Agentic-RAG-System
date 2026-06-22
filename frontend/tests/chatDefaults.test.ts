import { describe, expect, it } from "vitest";
import { resolveHybridExpertMode, resolveStreamFastMode } from "../src/lib/chatDefaults";

describe("chatDefaults", () => {
  it("uses server hybrid default when no session override", () => {
    expect(resolveHybridExpertMode({ hybrid_expert_mode: true }, null)).toBe(true);
    expect(resolveHybridExpertMode({ hybrid_expert_mode: false }, null)).toBe(false);
    expect(resolveHybridExpertMode(null, null)).toBe(false);
  });

  it("session override wins over server default", () => {
    expect(resolveHybridExpertMode({ hybrid_expert_mode: false }, true)).toBe(true);
    expect(resolveHybridExpertMode({ hybrid_expert_mode: true }, false)).toBe(false);
  });

  it("passes stream_fast_mode from server config", () => {
    expect(resolveStreamFastMode({ stream_fast_mode: true })).toBe(true);
    expect(resolveStreamFastMode({ stream_fast_mode: false })).toBe(false);
    expect(resolveStreamFastMode(null)).toBeUndefined();
  });
});
