import { describe, expect, it } from "vitest";
import { splitNeedByPaperDiff } from "../src/pages/admin/exam-bank/ExamDiffProportionCard";

describe("splitNeedByPaperDiff", () => {
  it("splits mid paper 10 into 2/6/2", () => {
    expect(splitNeedByPaperDiff(10, "mid")).toEqual({ easy: 2, mid: 6, hard: 2 });
  });

  it("keeps sum equal to need for easy/hard", () => {
    for (const mode of ["easy", "mid", "hard"] as const) {
      for (const n of [0, 1, 3, 7, 11]) {
        const r = splitNeedByPaperDiff(n, mode);
        expect(r.easy + r.mid + r.hard).toBe(n);
        expect(r.easy).toBeGreaterThanOrEqual(0);
        expect(r.mid).toBeGreaterThanOrEqual(0);
        expect(r.hard).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("easy paper prefers easy band", () => {
    const r = splitNeedByPaperDiff(10, "easy");
    expect(r.easy).toBeGreaterThanOrEqual(r.mid);
    expect(r.hard).toBe(0);
  });
});
