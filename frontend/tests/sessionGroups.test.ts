/**
 * groupSessionsByDate — P1 SessionList 分组逻辑（今天/昨天/近7天/更早）。
 */
import { describe, it, expect } from "vitest";
import { groupSessionsByDate } from "../src/lib/sessionGroups";
import type { ChatSession } from "../src/api/types";

const NOW = new Date("2026-08-03T15:00:00");

function s(id: string, updated_at?: string): ChatSession {
  return { id, title: `对话${id}`, updated_at };
}

describe("groupSessionsByDate", () => {
  it("returns empty array for no sessions", () => {
    expect(groupSessionsByDate([], NOW)).toEqual([]);
  });

  it("groups today / yesterday / last-7-days / earlier", () => {
    const sessions = [
      s("a", "2026-08-03T09:20:00"), // 今天
      s("b", "2026-08-02T23:10:00"), // 昨天
      s("c", "2026-07-30T08:00:00"), // 近7天
      s("d", "2026-07-20T12:00:00"), // 更早
    ];
    const groups = groupSessionsByDate(sessions, NOW);
    expect(groups.map((g) => g.label)).toEqual(["今天", "昨天", "近 7 天", "更早"]);
    expect(groups[0].items.map((x) => x.id)).toEqual(["a"]);
    expect(groups[1].items.map((x) => x.id)).toEqual(["b"]);
    expect(groups[2].items.map((x) => x.id)).toEqual(["c"]);
    expect(groups[3].items.map((x) => x.id)).toEqual(["d"]);
  });

  it("omits empty groups", () => {
    const sessions = [s("a", "2026-08-03T01:00:00"), s("d", "2025-12-31T00:00:00")];
    const groups = groupSessionsByDate(sessions, NOW);
    expect(groups.map((g) => g.label)).toEqual(["今天", "更早"]);
  });

  it("puts sessions without updated_at into 更早", () => {
    const groups = groupSessionsByDate([s("x")], NOW);
    expect(groups).toHaveLength(1);
    expect(groups[0].label).toBe("更早");
  });

  it("preserves input order within a group", () => {
    const sessions = [
      s("a", "2026-08-03T10:00:00"),
      s("b", "2026-08-03T08:00:00"),
    ];
    const groups = groupSessionsByDate(sessions, NOW);
    expect(groups[0].items.map((x) => x.id)).toEqual(["a", "b"]);
  });

  it("handles ISO strings with timezone", () => {
    const groups = groupSessionsByDate([s("a", "2026-08-03T14:30:00+08:00")], NOW);
    expect(groups[0].label).toBe("今天");
  });
});
