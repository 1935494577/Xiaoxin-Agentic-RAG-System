import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

describe("vite dev proxy", () => {
  it("proxies chat API subpaths but not the SPA /chat route", () => {
    const src = readFileSync(join(__dirname, "../vite.config.ts"), "utf8");
    expect(src).not.toMatch(/["']\/chat["']\s*:\s*\{/);
    expect(src).toContain('"/chat/sessions"');
    expect(src).toContain('"/chat/stream"');
    expect(src).toContain("sseProxy");
    expect(src).toContain("x-accel-buffering");
  });
});
