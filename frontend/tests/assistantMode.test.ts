import { describe, it, expect, beforeEach } from "vitest";
import {
  ASSISTANT_MODE_STORAGE_KEY,
  loadStoredAssistantMode,
  normalizeAssistantMode,
  placeholderForMode,
  resolveDefaultAssistantMode,
  saveStoredAssistantMode,
} from "../src/lib/assistantMode";

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(globalThis, "localStorage", { value: localStorageMock });

describe("assistantMode", () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it("normalizes invalid modes to auto", () => {
    expect(normalizeAssistantMode("nope")).toBe("auto");
    expect(normalizeAssistantMode("knowledge")).toBe("knowledge");
  });

  it("persists mode in localStorage", () => {
    saveStoredAssistantMode("task");
    expect(localStorageMock.getItem(ASSISTANT_MODE_STORAGE_KEY)).toBe("task");
    expect(loadStoredAssistantMode()).toBe("task");
  });

  it("resolveDefaultAssistantMode prefers stored over ui", () => {
    expect(resolveDefaultAssistantMode("knowledge", "task")).toBe("task");
    expect(resolveDefaultAssistantMode("knowledge", null)).toBe("knowledge");
  });

  it("placeholderForMode differs by mode", () => {
    expect(placeholderForMode("task")).toContain("任务");
    expect(placeholderForMode("knowledge")).toContain("知识库");
    expect(placeholderForMode("auto")).toContain("自动");
  });
});
