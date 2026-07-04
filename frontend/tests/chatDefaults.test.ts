import { describe, it, expect } from "vitest";
import { resolveStreamFastMode } from "../src/lib/chatDefaults";

describe("chatDefaults", () => {
  it("resolveStreamFastMode uses server config", () => {
    expect(resolveStreamFastMode({ stream_fast_mode: true })).toBe(true);
    expect(resolveStreamFastMode({ stream_fast_mode: false })).toBe(false);
    expect(resolveStreamFastMode(null)).toBeUndefined();
  });
});
