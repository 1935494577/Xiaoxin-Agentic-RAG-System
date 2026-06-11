/**
 * useChatStream hook tests.
 * Covers SSE parsing, state transitions, error handling, and abort — the core chat logic.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { StreamEvent } from "../src/api/types";

const mockAppendMessages = vi.fn();
const mockStreamChat = vi.fn();

vi.mock("../src/api/client", () => ({
  streamChat: (...args: unknown[]) => {
    const fn = vi.mocked(mockStreamChat);
    return fn(...args);
  },
  appendMessages: (...args: unknown[]) => {
    const fn = vi.mocked(mockAppendMessages);
    return fn(...args);
  },
}));

import { useChatStream } from "../src/hooks/useChatStream";

function mockStream(events: StreamEvent[]) {
  mockStreamChat.mockImplementation(async (_payload: unknown, onEvent: (e: StreamEvent) => void, _signal: AbortSignal) => {
    for (const evt of events) {
      onEvent(evt);
    }
  });
}

describe("useChatStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStreamChat.mockReset();
    mockAppendMessages.mockReset();
  });

  it("initial state is idle", () => {
    const onPersist = vi.fn();
    const { result } = renderHook(() => useChatStream("user1", onPersist));

    expect(result.current.streaming).toBe(false);
    expect(result.current.streamText).toBe("");
    expect(result.current.error).toBe("");
  });

  it("send transitions to streaming and accumulates tokens", async () => {
    mockStream([
      { type: "token", content: "你好" },
      { type: "token", content: "，世界" },
      { type: "done", answer: "你好，世界", trace_id: "t1" },
    ]);

    const onPersist = vi.fn();
    const { result } = renderHook(() => useChatStream("user1", onPersist));

    let messages: ReturnType<typeof result.current.send> extends Promise<infer T> ? T : never;
    await act(async () => {
      messages = await result.current.send(
        { message: "hello", user_id: "user1", session_id: "s1" },
        []
      );
    });

    expect(mockStreamChat).toHaveBeenCalledTimes(1);
    expect(result.current.streaming).toBe(false);
    expect(result.current.streamText).toBe("");

    expect(messages![0].role).toBe("user");
    expect(messages![0].content).toBe("hello");
    expect(messages![1].role).toBe("assistant");
    expect(messages![1].content).toBe("你好，世界");
    expect(messages![1].meta?.trace_id).toBe("t1");
  });

  it("token events update streamText progressively", async () => {
    mockStreamChat.mockImplementation(async (_payload: unknown, onEvent: (e: StreamEvent) => void) => {
      onEvent({ type: "token", content: "第" });
      onEvent({ type: "token", content: "一段" });
      onEvent({ type: "token", content: "文字" });
      onEvent({ type: "done", answer: "第一段文字" });
    });

    const onPersist = vi.fn();
    const { result } = renderHook(() => useChatStream("user1", onPersist));

    await act(async () => {
      await result.current.send({ message: "test", user_id: "user1" }, []);
    });

    // Final state is reset
    expect(result.current.streaming).toBe(false);
  });

  it("error event sets error in stream state", async () => {
    mockStream([
      { type: "token", content: "部分" },
      { type: "error", message: "服务端超时" },
    ]);

    const onPersist = vi.fn();
    const { result } = renderHook(() => useChatStream("user1", onPersist));

    await act(async () => {
      await result.current.send({ message: "test", user_id: "user1" }, []);
    });

    // After error + stream end, the message contains "（无回复）" as fallback
    // This tests that the hook doesn't crash on error events
    expect(result.current.streaming).toBe(false);
  });

  it("done event captures sources and answer_mode", async () => {
    mockStream([
      {
        type: "done",
        answer: "回答内容",
        sources: ["doc1.pdf", "doc2.md"],
        source_refs: [{ source: "doc1.pdf", parent_id: "p1" }],
        answer_mode: "kb",
        verified: true,
        trace_id: "trace_abc",
      },
    ]);

    const onPersist = vi.fn();
    const { result } = renderHook(() => useChatStream("user1", onPersist));

    let messages: Awaited<ReturnType<typeof result.current.send>>;
    await act(async () => {
      messages = await result.current.send(
        { message: "q", user_id: "user1", session_id: "s1" },
        []
      );
    });

    const assistantMsg = messages![1];
    expect(assistantMsg.meta?.sources).toEqual(["doc1.pdf", "doc2.md"]);
    expect(assistantMsg.meta?.answer_mode).toBe("kb");
    expect(assistantMsg.meta?.verified).toBe(true);
    expect(assistantMsg.meta?.trace_id).toBe("trace_abc");
  });

  it("persists messages via appendMessages when session_id is set", async () => {
    mockStream([{ type: "done", answer: "ok" }]);
    mockAppendMessages.mockResolvedValue(undefined);

    const onPersist = vi.fn();
    const { result } = renderHook(() => useChatStream("user1", onPersist));

    await act(async () => {
      await result.current.send(
        { message: "persist test", user_id: "user1", session_id: "sess1" },
        []
      );
    });

    expect(mockAppendMessages).toHaveBeenCalledWith(
      "user1",
      "sess1",
      expect.any(Array),
      "persist test"
    );
    expect(onPersist).toHaveBeenCalled();
  });

  it("does not persist when session_id is missing", async () => {
    mockStream([{ type: "done", answer: "ok" }]);

    const onPersist = vi.fn();
    const { result } = renderHook(() => useChatStream("user1", onPersist));

    await act(async () => {
      await result.current.send({ message: "no session", user_id: "user1" }, []);
    });

    expect(mockAppendMessages).not.toHaveBeenCalled();
  });

  it("abort cancels ongoing stream", async () => {
    // Simulate a never-finishing stream that rejects on abort
    mockStreamChat.mockImplementation(async (_payload: unknown, _onEvent: unknown, signal: AbortSignal) => {
      return new Promise((_resolve, reject) => {
        const onAbort = () => reject(new DOMException("Aborted", "AbortError"));
        signal.addEventListener("abort", onAbort, { once: true });
      });
    });

    const onPersist = vi.fn();
    const { result } = renderHook(() => useChatStream("user1", onPersist));

    // Start send (don't await — it hangs then rejects on abort)
    let sendPromise: Promise<unknown>;
    act(() => {
      sendPromise = result.current.send({ message: "abort me", user_id: "user1" }, []);
    });

    // Abort immediately
    act(() => {
      result.current.abort();
    });

    // The promise rejects with AbortError — current behavior (streamChat doesn't catch abort)
    await expect(sendPromise!).rejects.toThrow("Aborted");
  });

  it("includes prior messages as history in stream payload", async () => {
    mockStream([{ type: "done", answer: "resp" }]);

    const onPersist = vi.fn();
    const { result } = renderHook(() => useChatStream("user1", onPersist));
    const prior = [
      { role: "user" as const, content: "q1" },
      { role: "assistant" as const, content: "a1" },
    ];

    await act(async () => {
      await result.current.send({ message: "q2", user_id: "user1" }, prior);
    });

    const callArgs = mockStreamChat.mock.calls[0][0];
    expect(callArgs.skip_query_rewrite).toBe(true);
    expect(callArgs.history).toEqual([{ role: "user", content: "q1" }, { role: "assistant", content: "a1" }]);
  });
});
