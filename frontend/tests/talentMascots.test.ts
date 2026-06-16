import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { TALENT_MASCOTS, TALENT_DISPLAY_ORDER } from "../src/lib/talentMascots";

const PUBLIC = resolve(import.meta.dirname, "../public/talents");

/** PNG 宽高比约 1:1；用文件大小区间区分五张素材，防止复制时文件名与内容错位 */
const ASSET_SIGNATURE: Record<string, { minBytes: number; maxBytes: number }> = {
  "si.jpg": { minBytes: 43_000, maxBytes: 44_500 },
  "ying.jpg": { minBytes: 51_000, maxBytes: 52_500 },
  "xue.jpg": { minBytes: 49_000, maxBytes: 50_500 },
  "de.jpg": { minBytes: 47_500, maxBytes: 49_000 },
  "xing.jpg": { minBytes: 58_500, maxBytes: 60_000 },
};

describe("talentMascots", () => {
  it("displays left-to-right: 思者→德者→学者→行者→赢者", () => {
    expect(TALENT_DISPLAY_ORDER).toEqual(["si", "de", "xue", "xing", "ying"]);
    expect(TALENT_MASCOTS.map((t) => t.name)).toEqual([
      "思者",
      "德者",
      "学者",
      "行者",
      "赢者",
    ]);
  });

  it("maps accent colors to reference icons", () => {
    expect(TALENT_MASCOTS.find((t) => t.id === "si")).toMatchObject({
      accent: "#43A047",
      src: "/talents/xue.jpg",
    });
    expect(TALENT_MASCOTS.find((t) => t.id === "xue")).toMatchObject({
      accent: "#1E88E5",
      src: "/talents/xing.jpg",
    });
    expect(TALENT_MASCOTS.find((t) => t.id === "xing")).toMatchObject({
      accent: "#FFB300",
      src: "/talents/si.jpg",
    });
  });

  it("maps abilities and brain tiers from 天赋基础知识.txt", () => {
    expect(TALENT_MASCOTS.find((t) => t.id === "si")).toMatchObject({
      ability: "创造力",
      brain: "右脑5",
    });
    expect(TALENT_MASCOTS.find((t) => t.id === "ying")).toMatchObject({
      ability: "想象力",
      brain: "右脑4",
    });
    expect(TALENT_MASCOTS.find((t) => t.id === "xue")).toMatchObject({
      ability: "专注力",
      brain: "平衡3",
    });
    expect(TALENT_MASCOTS.find((t) => t.id === "de")).toMatchObject({
      ability: "观察力",
      brain: "左脑4",
    });
    expect(TALENT_MASCOTS.find((t) => t.id === "xing")).toMatchObject({
      ability: "记忆力",
      brain: "左脑5",
    });
  });

  it("each asset exists and matches expected file (JPEG fingerprint)", () => {
    for (const talent of TALENT_MASCOTS) {
      const filename = talent.src.replace("/talents/", "");
      const path = resolve(PUBLIC, filename);
      const buf = readFileSync(path);
      expect(buf.subarray(0, 3).toString("hex")).toBe("ffd8ff");
      const sig = ASSET_SIGNATURE[filename];
      expect(buf.length).toBeGreaterThanOrEqual(sig.minBytes);
      expect(buf.length).toBeLessThanOrEqual(sig.maxBytes);
    }
  });
});
