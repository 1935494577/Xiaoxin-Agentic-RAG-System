import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { shouldServeAdminSpa } from "../vite/adminProxyBypass";

function htmlGet(url: string) {
  return {
    method: "GET",
    url,
    headers: { accept: "text/html,application/xhtml+xml" },
  } as import("node:http").IncomingMessage;
}

function jsonGet(url: string) {
  return {
    method: "GET",
    url,
    headers: { accept: "application/json" },
  } as import("node:http").IncomingMessage;
}

describe("adminProxyBypass", () => {
  it("serves SPA for browser refresh on admin pages", () => {
    expect(shouldServeAdminSpa(htmlGet("/admin/prompts"))).toBe(true);
    expect(shouldServeAdminSpa(htmlGet("/admin/memory"))).toBe(true);
    expect(shouldServeAdminSpa(htmlGet("/admin/feedback"))).toBe(true);
  });

  it("still proxies admin API fetches", () => {
    expect(shouldServeAdminSpa(jsonGet("/admin/feedback"))).toBe(false);
    expect(shouldServeAdminSpa(jsonGet("/admin/feedback/stats?since_days=7"))).toBe(false);
  });

  it("vite config uses admin API proxy bypass", () => {
    const src = readFileSync(join(__dirname, "../vite.config.ts"), "utf8");
    expect(src).toContain("adminApiProxy");
    expect(src).not.toMatch(/["']\/admin["']\s*:\s*apiProxy\(\)/);
  });
});
