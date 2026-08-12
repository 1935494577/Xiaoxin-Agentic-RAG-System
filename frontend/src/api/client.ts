import type {
  LoginResponse,
  ChatMessage,
  ChatSession,
  FeedbackListResponse,
  FeedbackPayload,
  FeedbackStats,
  SourcePreview,
  EphemeralDoc,
  IngestedSource,
  ModelProfile,
  ModelProfilesData,
  ProcessingToolsData,
  ProcessingToolsSave,
  AgentToolsData,
  AgentToolsSave,
  McpCacheResetResponse,
  McpConfigData,
  McpConfigSave,
  PromptData,
  StreamEvent,
  StreamPayload,
  ScenarioCatalogResponse,
  TraceStatus,
  UiConfig,
  UserProfile,
  UserProfileUpdate,
  VectorStore,
} from "./types";
import { AUTH_SESSION_KEY } from "../lib/constants";
import { resolveAdminRole, type AdminRole } from "../lib/adminRoles";

/** Exported for authenticated media fetches (e.g. EQ formula <img> via blob). */
export function readAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  try {
    const raw =
      localStorage.getItem(AUTH_SESSION_KEY) ?? sessionStorage.getItem(AUTH_SESSION_KEY);
    if (!raw) return headers;
    const session = JSON.parse(raw) as {
      username?: string;
      department?: string;
      role?: AdminRole;
      token?: string;
    };
    if (session.token?.trim()) {
      headers["Authorization"] = `Bearer ${session.token.trim()}`;
    }
    if (session.department?.trim()) {
      headers["X-User-Department"] = encodeURIComponent(session.department.trim());
    }
    if (session.username?.trim()) {
      headers["X-User-Name"] = encodeURIComponent(session.username.trim());
    }
    const role = session.role ?? resolveAdminRole(session.department ?? "");
    headers["X-Admin-Role"] = role;
  } catch {
    /* ignore malformed session */
  }
  return headers;
}

// ===== Base fetch wrapper =====
async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number }
): Promise<T> {
  const { timeoutMs = 60_000, ...fetchInit } = init ?? {};
  const authHeaders = readAuthHeaders();
  const headers = new Headers(fetchInit.headers);
  for (const [key, value] of Object.entries(authHeaders)) {
    if (!headers.has(key)) headers.set(key, value);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let r: Response;
  try {
    r = await fetch(path, { ...fetchInit, headers, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("请求超时，请确认后端 API 已启动（8010 端口）");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
  if (r.status === 401) {
    localStorage.removeItem(AUTH_SESSION_KEY);
    sessionStorage.removeItem(AUTH_SESSION_KEY);
    const from = encodeURIComponent(window.location.pathname + window.location.search);
    if (!window.location.pathname.startsWith("/login")) {
      window.location.assign(`/login?from=${from}`);
    }
    throw new Error("Unauthorized");
  }
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  return r.json() as Promise<T>;
}

export function apiGet<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  return request<T>(path, init);
}

export function apiRequest<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  return request<T>(path, init);
}

/** Binary download (PDF/DOCX/etc). Returns blob + filename from Content-Disposition when present. */
export async function apiFetchBlob(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<{ blob: Blob; filename: string | null }> {
  const { timeoutMs = 60_000, ...fetchInit } = init ?? {};
  const authHeaders = readAuthHeaders();
  const headers = new Headers(fetchInit.headers);
  for (const [key, value] of Object.entries(authHeaders)) {
    if (!headers.has(key)) headers.set(key, value);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let r: Response;
  try {
    r = await fetch(path, { ...fetchInit, headers, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("请求超时，请确认后端 API 已启动（8010 端口）");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
  if (r.status === 401) {
    localStorage.removeItem(AUTH_SESSION_KEY);
    sessionStorage.removeItem(AUTH_SESSION_KEY);
    const from = encodeURIComponent(window.location.pathname + window.location.search);
    if (!window.location.pathname.startsWith("/login")) {
      window.location.assign(`/login?from=${from}`);
    }
    throw new Error("Unauthorized");
  }
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  const cd = r.headers.get("Content-Disposition") || "";
  let filename: string | null = null;
  const star = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(cd);
  const plain = /filename\s*=\s*"?([^";]+)"?/i.exec(cd);
  if (star?.[1]) {
    try {
      filename = decodeURIComponent(star[1].trim());
    } catch {
      filename = star[1].trim();
    }
  } else if (plain?.[1]) {
    filename = plain[1].trim();
  }
  return { blob: await r.blob(), filename };
}

// ===== UI & Nav =====
export function authLogin(
  username: string,
  password: string,
  remember = true
): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, remember }),
    timeoutMs: 30_000,
  });
}

export function authLogout(): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/auth/logout", { method: "POST" });
}

export function authMe(): Promise<LoginResponse["user"]> {
  return request<LoginResponse["user"]>("/auth/me");
}

export function authChangePassword(
  currentPassword: string,
  newPassword: string
): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export type AdminUserRow = {
  id: string;
  username: string;
  department: string;
  display_name: string;
  is_active: boolean;
};

export function fetchAdminUsers(): Promise<AdminUserRow[]> {
  return request<{ users: AdminUserRow[] }>("/auth/admin/users").then((r) => r.users);
}

export function createAdminUser(body: {
  username: string;
  password: string;
  department: string;
  display_name?: string;
}): Promise<AdminUserRow> {
  return request<AdminUserRow>("/auth/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function setAdminUserActive(userId: string, isActive: boolean): Promise<void> {
  return request(`/auth/admin/users/${encodeURIComponent(userId)}/active`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
  });
}

export function resetAdminUserPassword(userId: string, newPassword: string): Promise<void> {
  return request(`/auth/admin/users/${encodeURIComponent(userId)}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword }),
  });
}

export function fetchUiConfig(): Promise<UiConfig> {
  return request<UiConfig>("/config/ui");
}

export function fetchScenarioCatalog(options?: {
  department?: string;
  includeTech?: boolean;
}): Promise<ScenarioCatalogResponse> {
  const q = new URLSearchParams();
  if (options?.department?.trim()) q.set("department", options.department.trim());
  if (options?.includeTech === true) q.set("include_tech", "true");
  if (options?.includeTech === false) q.set("include_tech", "false");
  const suffix = q.toString() ? `?${q}` : "";
  return request<ScenarioCatalogResponse>(`/config/scenario-catalog${suffix}`);
}

// ===== User profile =====
export function fetchUserProfile(userId: string): Promise<UserProfile> {
  return request<UserProfile>(`/users/profile?user_id=${encodeURIComponent(userId)}`);
}

export function saveUserProfile(body: UserProfileUpdate): Promise<UserProfile> {
  return request<UserProfile>("/users/profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function mergeLegacyUserProfile(legacyUserId: string): Promise<UserProfile> {
  return request<UserProfile>("/users/profile/merge-legacy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ legacy_user_id: legacyUserId }),
  });
}

// ===== Sessions =====
export function listSessions(): Promise<ChatSession[]> {
  return request<ChatSession[]>("/chat/sessions");
}

export function createSession(title = "新对话"): Promise<ChatSession> {
  return request<ChatSession>("/chat/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export function deleteSession(sessionId: string): Promise<void> {
  return request(`/chat/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

// ===== Messages =====
export function loadMessages(sessionId: string): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`);
}

export function appendMessages(
  sessionId: string,
  messages: ChatMessage[],
  autoTitleFrom?: string
): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, auto_title_from: autoTitleFrom }),
  });
}

export function listIngestedSources(): Promise<IngestedSource[]> {
  return request<IngestedSource[]>("/sources/list");
}

export function deleteIngestedSource(source: string): Promise<void> {
  return request(`/sources/${encodeURIComponent(source)}`, { method: "DELETE" });
}

export async function uploadChatDocument(
  file: File,
  sessionId: string,
): Promise<EphemeralDoc> {
  const form = new FormData();
  form.append("file", file);
  const q = new URLSearchParams({ session_id: sessionId });
  const authHeaders = readAuthHeaders();
  const headers = new Headers(authHeaders);
  const r = await fetch(`/chat/documents/upload?${q}`, { method: "POST", body: form, headers });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  return r.json() as Promise<EphemeralDoc>;
}

export async function transcribeAudio(
  blob: Blob,
  language = "zh"
): Promise<{ text: string }> {
  const ext = blob.type.includes("mp4")
    ? "m4a"
    : blob.type.includes("mpeg")
      ? "mp3"
      : blob.type.includes("wav")
        ? "wav"
        : "webm";
  const form = new FormData();
  form.append("file", blob, `speech.${ext}`);
  const authHeaders = readAuthHeaders();
  const headers = new Headers(authHeaders);
  const q = new URLSearchParams({ language });
  const r = await fetch(`/chat/transcribe?${q}`, { method: "POST", body: form, headers });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || r.statusText);
  }
  return r.json() as Promise<{ text: string }>;
}

// ===== SSE Streaming =====
export async function streamChat(
  payload: StreamPayload,
  onEvent: (evt: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const authHeaders = readAuthHeaders();
  const headers = new Headers({
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  });
  for (const [key, value] of Object.entries(authHeaders)) {
    headers.set(key, value);
  }
  let r: Response;
  try {
    r = await fetch("/chat/stream", {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      signal,
      cache: "no-store",
    });
  } catch (err) {
    if (signal?.aborted) return;
    throw err;
  }
  if (!r.ok) {
    const text = await r.text();
    let message = text || r.statusText || "请求失败";
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      }
    } catch {
      /* plain-text error body */
    }
    onEvent({ type: "error", message });
    return;
  }
  const reader = r.body?.getReader();
  if (!reader) return;
  const dec = new TextDecoder();
  let buf = "";
  const flushLines = (chunk: string) => {
    buf += chunk;
    const lines = buf.split("\n");
    buf = lines.pop() || "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const evt = JSON.parse(line.slice(6)) as StreamEvent;
        onEvent(evt);
      } catch {
        /* ignore malformed */
      }
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (value) {
        flushLines(dec.decode(value, { stream: true }));
      }
      if (done) break;
    }
    if (buf.trim()) {
      flushLines("\n");
    }
  } catch (err) {
    if (signal?.aborted) {
      try {
        await reader.cancel();
      } catch {
        /* ignore */
      }
      return;
    }
    throw err;
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
      message_id: opts.message_id ?? opts.trace_id,
      trace_id: opts.trace_id ?? opts.message_id,
      session_id: opts.session_id,
      question: opts.question,
      answer_preview: opts.answer_preview,
      answer_mode: opts.answer_mode,
      correction: opts.correction,
    }),
  });
}

export function fetchFeedbackList(params?: {
  user_id?: string;
  trace_id?: string;
  rating?: number;
  status?: string;
  sort?: "created_desc" | "severity_desc" | "severity_asc";
  since_days?: number;
  offset?: number;
  limit?: number;
}): Promise<FeedbackListResponse> {
  const q = new URLSearchParams();
  if (params?.user_id) q.set("user_id", params.user_id);
  if (params?.trace_id) q.set("trace_id", params.trace_id);
  if (params?.rating !== undefined) q.set("rating", String(params.rating));
  if (params?.status) q.set("status", params.status);
  if (params?.sort) q.set("sort", params.sort);
  if (params?.since_days !== undefined) q.set("since_days", String(params.since_days));
  if (params?.offset !== undefined) q.set("offset", String(params.offset));
  if (params?.limit !== undefined) q.set("limit", String(params.limit));
  const qs = q.toString();
  return request<FeedbackListResponse>(`/admin/feedback${qs ? `?${qs}` : ""}`);
}

export function fetchFeedbackStats(sinceDays = 7): Promise<FeedbackStats> {
  return request<FeedbackStats>(`/admin/feedback/stats?since_days=${sinceDays}`);
}

export function fetchSourcePreview(
  parentId: string,
  userDepartment: string
): Promise<SourcePreview> {
  const params = new URLSearchParams({ user_department: userDepartment });
  return request<SourcePreview>(`/sources/preview/${encodeURIComponent(parentId)}?${params}`);
}

export function runFeedbackTriage(opts?: {
  limit?: number;
  use_llm?: boolean;
  rating?: number;
}): Promise<{ processed: number; failed: number; queued: number }> {
  return request("/admin/feedback/triage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      limit: opts?.limit ?? 20,
      use_llm: opts?.use_llm ?? false,
      rating: opts?.rating,
    }),
  });
}

export type FeedbackActionResult = {
  action: string;
  ok: boolean;
  skipped?: boolean;
  reason?: string;
  error?: string;
  revision_id?: string;
  proposal_id?: string;
  golden_path?: string;
};

export function approveFeedback(
  id: string,
): Promise<{ id: string; status: string; action_results?: FeedbackActionResult[] }> {
  return request(`/admin/feedback/${encodeURIComponent(id)}/approve`, { method: "POST" });
}

export function rejectFeedback(id: string): Promise<{ id: string; status: string }> {
  return request(`/admin/feedback/${encodeURIComponent(id)}/reject`, { method: "POST" });
}

export function fetchFeedbackTrace(traceId: string): Promise<Record<string, unknown>> {
  return request(`/admin/feedback/traces/${encodeURIComponent(traceId)}`);
}

export function exportFeedbackJsonl(): Promise<{ ok: boolean; exported: number }> {
  return request("/admin/feedback/export-jsonl", { method: "POST" });
}

export type EvalReportItem = {
  id: string;
  created_at: string;
  feedback_id?: string | null;
  revision_id?: string | null;
  golden_rows: number;
  mode: string;
  metrics: Record<string, unknown>;
  baseline_metrics: Record<string, unknown>;
  delta: Record<string, number>;
};

export function runFeedbackEvaluate(opts?: {
  feedback_id?: string;
  revision_id?: string;
}): Promise<{
  ok: boolean;
  report_id?: string;
  golden_rows?: number;
  mode?: string;
  metrics?: Record<string, unknown>;
  delta?: Record<string, number>;
  error?: string;
}> {
  return request("/admin/feedback/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      feedback_id: opts?.feedback_id,
      revision_id: opts?.revision_id,
    }),
  });
}

export function fetchEvalReports(params?: {
  feedback_id?: string;
  offset?: number;
  limit?: number;
}): Promise<{ items: EvalReportItem[]; total: number; limit: number; offset: number }> {
  const q = new URLSearchParams();
  if (params?.feedback_id) q.set("feedback_id", params.feedback_id);
  if (params?.offset !== undefined) q.set("offset", String(params.offset));
  if (params?.limit !== undefined) q.set("limit", String(params.limit));
  const qs = q.toString();
  return request(`/admin/feedback/eval-reports${qs ? `?${qs}` : ""}`);
}

export function exportEvalReports(): Promise<{
  ok: boolean;
  exported: number;
  items: EvalReportItem[];
}> {
  return request("/admin/feedback/eval-reports/export", { method: "POST" });
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

// ===== MCP Servers =====
export function fetchMcpConfig(): Promise<McpConfigData> {
  return request<McpConfigData>("/api/mcp/config");
}

export function saveMcpConfig(body: McpConfigSave): Promise<McpConfigData> {
  return request<McpConfigData>("/api/mcp/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function resetMcpCache(): Promise<McpCacheResetResponse> {
  return request<McpCacheResetResponse>("/api/mcp/cache/reset", { method: "POST" });
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

export function savePrompts(
  mode: string,
  slots: Record<string, unknown>[],
  fast?: boolean,
  extras?: { active_persona_id?: string; agent_reasoning_mode?: string; reset_defaults?: boolean }
): Promise<PromptData> {
  const params = new URLSearchParams({ mode });
  if (fast) params.set("fast", "true");
  return request<PromptData>(`/config/prompts?${params}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      slots,
      active_persona_id: extras?.active_persona_id,
      agent_reasoning_mode: extras?.agent_reasoning_mode,
      reset_defaults: extras?.reset_defaults,
    }),
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

export function applyScenePreset(presetId: string): Promise<UiConfig> {
  return request<UiConfig>(`/config/ui/scene-preset/${encodeURIComponent(presetId)}`, {
    method: "POST",
  });
}

// ===== IM Channels (DeerFlow-style runtime credentials) =====
export type ChannelCredentialField = {
  name: string;
  label: string;
  type: string;
  required: boolean;
};

export type ChannelConnectResponse = {
  provider: string;
  mode: string;
  url: string | null;
  code: string;
  instruction: string;
  expires_in: number;
};

export type ChannelProvider = {
  provider: string;
  display_name: string;
  enabled: boolean;
  configured: boolean;
  connectable: boolean;
  unavailable_reason: string | null;
  auth_mode: string;
  connection_status: string;
  credential_fields: ChannelCredentialField[];
  credential_values: Record<string, string>;
};

export type ChannelProvidersResponse = {
  enabled: boolean;
  providers: ChannelProvider[];
};

export type ChannelStatusResponse = {
  service_running: boolean;
  channels: Record<string, Record<string, unknown>>;
};

export function fetchChannelProviders(): Promise<ChannelProvidersResponse> {
  return request<ChannelProvidersResponse>("/api/channels/providers");
}

export function fetchChannelStatus(): Promise<ChannelStatusResponse> {
  return request<ChannelStatusResponse>("/api/channels/");
}

export function saveChannelRuntimeConfig(
  provider: string,
  values: Record<string, string>
): Promise<ChannelProvider> {
  return request<ChannelProvider>(`/api/channels/${encodeURIComponent(provider)}/runtime-config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values }),
  });
}

export function connectChannelProvider(provider: string): Promise<ChannelConnectResponse> {
  return request<ChannelConnectResponse>(`/api/channels/${encodeURIComponent(provider)}/connect`, {
    method: "POST",
  });
}

export function disconnectChannelProvider(provider: string): Promise<ChannelProvider> {
  return request<ChannelProvider>(`/api/channels/${encodeURIComponent(provider)}/runtime-config`, {
    method: "DELETE",
  });
}

export function fetchLlmHealth(): Promise<{ connected: boolean; message: string; model?: string; api_base?: string }> {
  return request("/health/llm");
}
