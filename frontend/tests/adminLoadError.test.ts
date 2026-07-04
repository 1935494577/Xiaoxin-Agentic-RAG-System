import { describe, it, expect } from "vitest";
import { formatAdminLoadError } from "../src/lib/adminLoadError";

describe("formatAdminLoadError", () => {
  it("parses 403 department detail", () => {
    const msg = formatAdminLoadError(
      new Error(
        JSON.stringify({
          detail: "当前部门无权访问该功能（processing）",
          department: "运营部",
        })
      ),
      "fallback"
    );
    expect(msg).toContain("无权");
    expect(msg).toContain("技术部");
  });

  it("detects network errors", () => {
    expect(formatAdminLoadError(new Error("Failed to fetch"), "fb")).toContain("无法连接");
  });
});
