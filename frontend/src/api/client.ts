import type {
  ChatMessage,
  ChatSession,
  FeedbackPayload,
  ModelProfile,
  ModelProfilesData,
  NavConfig,
  ProcessingToolsData,
  ProcessingToolsSave,
  AgentToolsData,
  AgentToolsSave,
  PromptData,
  StreamEvent,
  StreamPayload,
  TraceStatus,
  UiConfig,
  VectorStore,
} from "./types";

// ===== Base fetch wrapper =====
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  return r.json() as Promise<T>;
}

// ===== UI & Nav =====
export function fetchUiConfig(): Promise<UiConfig> {
  return request<UiConfig>("/config/ui");
}

export function fetchNav(): Promise<NavConfig> {
  return request<NavConfig>("/config/nav").catch(() => ({
    chat_url: window.location.origin,
    admin_url: window.location.origin,
    items: [],
  }));
}

// ===== Sessions =====
export function listSessions(userId: string): Promise<ChatSession[]> {
  return request<ChatSession[]>(`/chat/sessions?user_id=${encodeURIComponent(userId)}`);
}

export function createSession(userId: string, title = "新对话"): Promise<ChatSession> {
  return request<ChatSession>("/chat/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, title }),
  });
}

export function deleteSession(userId: string, sessionId: string): Promise<void> {
  return request(`/chat/sessions/${sessionId}?user_id=${encodeURIComponent(userId)}`, {
    method: "DELETE",
  });
}

// ===== Messages =====
export function loadMessages(userId: string, sessionId: string): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(
    `/chat/sessions/${sessionId}/messages?user_id=${encodeURIComponent(userId)}`
  );
}

export function appendMessages(
  userId: string,
  sessionId: string,
  messages: ChatMessage[],
  autoTitleFrom?: string
): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, messages, auto_title_from: autoTitleFrom }),
  });
}

// ===== SSE Streaming =====
export async function streamChat(
  payload: StreamPayload,
  onEvent: (evt: StreamEvent) => void,
  signal?: AbortSignal
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
        /* ignore malformed */
      }
    }
  }
}

// ===== Feedback =====
export function submitFeedback(opts: FeedbackPayload): Promise<void> {
  return request("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: opts.user_id,
      rating: opts.rating,
      message_id: opts.message_id,
    }),
  });
}

// ===== Model Profiles =====
export function fetchModelProfiles(): Promise<ModelProfilesData> {
  return request<ModelProfilesData>("/config/model-profiles");
}

export function testModelConnection(profileId: string): Promise<{ connected: boolean }> {
  return request(`/config/model-profiles/${profileId}/test`, { method: "POST" });
}

export function createModelProfile(body: Record<string, unknown>): Promise<ModelProfile> {
  return request<ModelProfile>("/config/model-profiles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function updateModelProfile(id: string, body: Record<string, unknown>): Promise<ModelProfile> {
  return request<ModelProfile>(`/config/model-profiles/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function testNewModelConnection(body: Record<string, unknown>): Promise<{ connected: boolean; message?: string }> {
  return request("/config/model-profiles/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function setDefaultModelProfile(id: string): Promise<void> {
  return request(`/config/model-profiles/${id}/default`, { method: "POST" });
}

export function deleteModelProfile(id: string): Promise<void> {
  return request(`/config/model-profiles/${id}`, { method: "DELETE" });
}

// ===== Processing Tools =====
export function fetchProcessingTools(): Promise<ProcessingToolsData> {
  return request<ProcessingToolsData>("/config/processing-tools");
}

export function saveProcessingTools(body: ProcessingToolsSave): Promise<ProcessingToolsData> {
  return request<ProcessingToolsData>("/config/processing-tools", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ===== Agent Chat Tools =====
export function fetchAgentTools(): Promise<AgentToolsData> {
  return request<AgentToolsData>("/config/agent-tools");
}

export function saveAgentTools(body: AgentToolsSave): Promise<AgentToolsData> {
  return request<AgentToolsData>("/config/agent-tools", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ===== Vector Stores =====
export function fetchVectorStores(): Promise<{ stores: VectorStore[]; active: string }> {
  return request("/config/vector-stores");
}

export function createVectorStore(name: string, backend: string): Promise<VectorStore> {
  return request("/config/vector-stores", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, backend }),
  });
}

export function activateVectorStore(id: string): Promise<void> {
  return request(`/config/vector-stores/${id}/activate`, { method: "PUT" });
}

export function deleteVectorStore(id: string): Promise<void> {
  return request(`/config/vector-stores/${id}`, { method: "DELETE" });
}

// ===== Prompts =====
export function fetchPrompts(mode: string, fast?: boolean): Promise<PromptData> {
  const params = new URLSearchParams({ mode });
  if (fast) params.set("fast", "true");
  return request<PromptData>(`/config/prompts?${params}`);
}

export function savePrompts(mode: string, slots: Record<string, unknown>[], fast?: boolean): Promise<void> {
  const params = new URLSearchParams({ mode });
  if (fast) params.set("fast", "true");
  return request(`/config/prompts?${params}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slots }),
  });
}

// ===== Trace =====
export function fetchTraceStatus(): Promise<TraceStatus> {
  return request<TraceStatus>("/debug/trace-status");
}

// ===== Ingest =====
export function uploadDocument(
  file: File,
  options: {
    department?: string;
    permission?: string;
    mode?: string;
    tags?: string[];
  }
): Promise<{ ok: boolean; message?: string }> {
  const form = new FormData();
  form.append("file", file);
  const params = new URLSearchParams();
  if (options.department) params.set("department", options.department);
  if (options.permission) params.set("permission_label", options.permission);
  if (options.mode) params.set("ingest_mode", options.mode);
  if (options.tags?.length) params.set("tags", options.tags.join(","));
  const qs = params.toString();
  return request(`/ingest/upload${qs ? "?" + qs : ""}`, {
    method: "POST",
    body: form,
  });
}

// ===== UI Config (admin write) =====
export function saveUiConfig(patch: Record<string, unknown>): Promise<void> {
  return request("/config/ui", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}
