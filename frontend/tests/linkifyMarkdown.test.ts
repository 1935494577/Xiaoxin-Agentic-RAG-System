import { describe, it, expect } from "vitest";
import {
  hrefForDomainOrUrl,
  isLinkableDomain,
  linkifyMarkdown,
} from "../src/lib/linkifyMarkdown";

describe("linkifyMarkdown", () => {
  it("linkifies bare domain in prose", () => {
    expect(linkifyMarkdown("域名 littlexin.com 已注册")).toBe(
      "域名 [littlexin.com](https://littlexin.com) 已注册",
    );
  });

  it("linkifies bold domain", () => {
    expect(linkifyMarkdown("如 **littlexin.com** 变体")).toBe(
      "如 [**littlexin.com**](https://littlexin.com) 变体",
    );
  });

  it("skips inline code", () => {
    expect(linkifyMarkdown("代码 `littlexin.com` 不链接")).toBe(
      "代码 `littlexin.com` 不链接",
    );
  });

  it("skips fenced code", () => {
    const md = "文本\n\n```\nlittlexin.com\n```\n\n结尾";
    expect(linkifyMarkdown(md)).toBe(md);
  });

  it("skips existing markdown links", () => {
    const md = "[littlexin.com](https://littlexin.com)";
    expect(linkifyMarkdown(md)).toBe(md);
  });
});

describe("isLinkableDomain", () => {
  it("accepts common domains", () => {
    expect(isLinkableDomain("littlexin.com")).toBe(true);
    expect(isLinkableDomain("api.reefapi.com")).toBe(true);
    expect(isLinkableDomain(".cn")).toBe(false);
    expect(isLinkableDomain("hello")).toBe(false);
  });
});

describe("hrefForDomainOrUrl", () => {
  it("adds https for domains", () => {
    expect(hrefForDomainOrUrl("littlexin.com")).toBe("https://littlexin.com");
  });
});
