import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { streamChat } from "../src/api/client";

describe("streamChat abort", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    });
    vi.stubGlobal("sessionStorage", {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("returns without throwing when fetch is aborted", async () => {
    const ctrl = new AbortController();
    ctrl.abort();

    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new DOMException("Aborted", "AbortError")))
    );

    const events: unknown[] = [];
    await expect(
      streamChat({ message: "hi", user_id: "u1" }, (evt) => events.push(evt), ctrl.signal)
    ).resolves.toBeUndefined();
    expect(events).toHaveLength(0);
  });

  it("returns without throwing when reader.read is aborted mid-stream", async () => {
    const ctrl = new AbortController();
    let reads = 0;

    const reader = {
      read: vi.fn(async () => {
        reads += 1;
        if (reads === 1) {
          ctrl.abort();
          throw new DOMException("Aborted", "AbortError");
        }
        return { done: true, value: undefined };
      }),
      cancel: vi.fn(async () => {}),
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        body: { getReader: () => reader },
      }))
    );

    const tokens: string[] = [];
    await expect(
      streamChat(
        { message: "hi", user_id: "u1" },
        (evt) => {
          if (evt.type === "token") tokens.push(evt.content);
        },
        ctrl.signal
      )
    ).resolves.toBeUndefined();
    expect(reader.cancel).toHaveBeenCalled();
  });
});
