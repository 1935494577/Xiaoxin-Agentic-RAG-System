import { describe, it, expect } from "vitest";
import { applyToolStreamEvent } from "../src/lib/streamTools";

describe("applyToolStreamEvent", () => {
  it("merges tool_call and tool_result", () => {
    let items = applyToolStreamEvent([], {
      type: "tool_call",
      tool: "get_weather",
      arguments: { city: "上海" },
    });
    items = applyToolStreamEvent(items, {
      type: "tool_result",
      tool: "get_weather",
      output: "上海 晴",
      ok: true,
    });
    expect(items).toHaveLength(1);
    expect(items[0].output).toBe("上海 晴");
    expect(items[0].arguments?.city).toBe("上海");
  });
});
