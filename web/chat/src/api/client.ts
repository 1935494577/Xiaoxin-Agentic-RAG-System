export type NavItem = {
  id: string;
  label: string;
  href: string;
  external?: boolean;
  primary?: boolean;
};

export type NavConfig = {
  chat_url: string;
  admin_url: string;
  items: NavItem[];
};

export type ChatSession = {
  id: string;
  title: string;
  updated_at?: string;
};

export type ChatMessage = {
  id?: string;
  role: "user" | "assistant";
  content: string;
  meta?: {
    sources?: string[];
    source_refs?: Array<{ source?: string; parent_id?: string }>;
    answer_mode?: string;
    verified?: boolean;
    trace_id?: string;
  };
};

export type StreamEvent =
  | { type: "status"; phase: string; answer_mode?: string }
  | { type: "token"; content: string }
  | { type: "error"; message: string }
  | {
      type: "done";
      answer: string;
      rewritten_query?: string;
      sources?: string[];
      source_refs?: Array<{ source?: string; parent_id?: string; department?: string }>;
      answer_mode?: string;
      verified?: boolean;
    };

const ADMIN_URL = import.meta.env.VITE_ADMIN_URL || "http://127.0.0.1:8501";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  return r.json() as Promise<T>;
}

export async function fetchNav(): Promise<NavConfig> {
  try {
    return await json<NavConfig>("/config/nav");
  } catch {
    return {
      chat_url: window.location.origin,
      admin_url: ADMIN_URL,
      items: [
        { id: "chat", label: "对话", href: window.location.origin, primary: true },
        { id: "ingest", label: "数据入库", href: `${ADMIN_URL}/ingest` },
        { id: "models", label: "模型", href: `${ADMIN_URL}/models` },
      ],
    };
  }
}

export async function listSessions(userId: string): Promise<ChatSession[]> {
  return json<ChatSession[]>(`/chat/sessions?user_id=${encodeURIComponent(userId)}`);
}

export async function createSession(userId: string, title = "新对话"): Promise<ChatSession> {
  return json<ChatSession>("/chat/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, title }),
  });
}

export async function deleteSession(userId: string, sessionId: string): Promise<void> {
  await json(`/chat/sessions/${sessionId}?user_id=${encodeURIComponent(userId)}`, { method: "DELETE" });
}

export async function loadMessages(userId: string, sessionId: string): Promise<ChatMessage[]> {
  return json<ChatMessage[]>(
    `/chat/sessions/${sessionId}/messages?user_id=${encodeURIComponent(userId)}`,
  );
}

export async function appendMessages(
  userId: string,
  sessionId: string,
  messages: ChatMessage[],
  autoTitleFrom?: string,
): Promise<ChatMessage[]> {
  return json<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, messages, auto_title_from: autoTitleFrom }),
  });
}

export async function submitFeedback(opts: {
  userId: string;
  rating: number;
  sessionId?: string;
  traceId?: string;
}): Promise<void> {
  await json("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: opts.userId,
      rating: opts.rating,
      message_id: opts.traceId,
    }),
  });
}

export async function streamChat(
  payload: Record<string, unknown>,
  onEvent: (evt: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const r = await fetch("/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!r.ok) {
    const text = await r.text();
    onEvent({ type: "error", message: text || "请求失败" });
    return;
  }
  const reader = r.body?.getReader();
  if (!reader) return;
  const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() || "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        onEvent(JSON.parse(line.slice(6)) as StreamEvent);
      } catch {
        /* ignore */
      }
    }
  }
}

export function userIdFromStorage(): string {
  const key = "rag_chat_user_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = `u_${Math.random().toString(36).slice(2, 14)}`;
    localStorage.setItem(key, id);
  }
  return id;
}
