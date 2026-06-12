// ===== Nav & UI Config =====
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

export type UiConfig = {
  app_title?: string;
  app_tagline?: string;
  logo_en?: string;
  logo_cn?: string;
  logo_image_path?: string;
  has_logo_image?: boolean;
  suggested_questions?: string[];
  stream_fast_mode?: boolean;
  max_history_turns?: number;
  max_history_chars?: number;
  kb_min_score?: number;
  kb_min_rerank_score?: number;
  kb_llm_judge?: boolean;
  general_fallback_enabled?: boolean;
  kb_post_stream_fallback?: boolean;
  hybrid_expert_mode?: boolean;
  stream_verifier_enabled?: boolean;
  graph_verifier_enabled?: boolean;
  long_term_memory_enabled?: boolean;
  ingest_tag_presets?: string[];
  supported_upload_extensions?: string[];
  supported_upload_label?: string;
};

// ===== Chat =====
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
    source_refs?: Array<{ source?: string; parent_id?: string; department?: string }>;
    answer_mode?: string;
    verified?: boolean;
    trace_id?: string;
    tool_trace?: ToolTraceItem[];
  };
};

export type ToolTraceItem = {
  tool: string;
  arguments?: Record<string, unknown>;
  output?: string;
  ok?: boolean;
};

export type StreamEvent =
  | { type: "status"; phase: string; answer_mode?: string; trace_id?: string }
  | { type: "stream_reset" }
  | { type: "token"; content: string }
  | { type: "tool_call"; tool: string; arguments: Record<string, unknown> }
  | { type: "tool_result"; tool: string; output: string; ok: boolean }
  | { type: "error"; message: string; trace_id?: string }
  | {
      type: "done";
      answer: string;
      rewritten_query?: string;
      sources?: string[];
      source_refs?: Array<{ source?: string; parent_id?: string; department?: string }>;
      answer_mode?: string;
      verified?: boolean;
      trace_id?: string;
      tool_trace?: ToolTraceItem[];
    };

export type StreamPayload = {
  message: string;
  user_id: string;
  user_department?: string;
  hybrid_expert_mode?: boolean;
  skip_query_rewrite?: boolean;
  session_id?: string;
  history?: Array<{ role: string; content: string }>;
};

// ===== Model Profiles =====
export type ModelProfile = {
  id: string;
  name: string;
  vendor: string;
  api_base?: string;
  api_path?: string;
  default_model?: string;
  has_api_key?: boolean;
};

export type ModelProfilesData = {
  profiles: ModelProfile[];
  default_profile_id: string;
};

// ===== Processing Tools =====
export type ProcessingTool = {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
};

export type ProcessingToolsData = {
  tools: ProcessingTool[];
  use_llm_router: boolean;
  extension_map?: Record<string, string>;
};

export type ProcessingToolsSave = {
  use_llm_router: boolean;
  tools: Record<string, { enabled: boolean }>;
};

// ===== Agent Chat Tools =====
export type AgentChatTool = {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
};

export type AgentToolsData = {
  chat_tools_enabled: boolean;
  tools: AgentChatTool[];
};

export type AgentToolsSave = {
  chat_tools_enabled: boolean;
  tools: Record<string, { enabled: boolean }>;
};

// ===== Vector Stores =====
export type VectorStore = {
  id: string;
  name: string;
  backend: string;
  active: boolean;
};

// ===== Prompts =====
export type PromptSlot = {
  id: string;
  label: string;
  scope: string[];
  category: string;
  builtin: boolean;
  enabled: boolean;
  order: number;
  template: string;
};

export type PromptData = {
  mode: string;
  slots: PromptSlot[];
  composite: string;
};

// ===== Trace =====
export type TraceStatus = {
  langsmith_enabled: boolean;
  langsmith_vars: Record<string, string>;
  local_trace_enabled: boolean;
  local_trace_file: string;
  local_trace_lines: number;
};

// ===== Feedback =====
export type FeedbackPayload = {
  user_id: string;
  rating: number;
  message_id?: string;
  trace_id?: string;
  session_id?: string;
  question?: string;
  answer_preview?: string;
  answer_mode?: string;
  correction?: string;
};

export type FeedbackSuggestedAction = {
  action: string;
  confidence?: number | null;
  detail?: string | null;
};

export type FeedbackItem = {
  id: string;
  tenant_id: string;
  user_id: string;
  rating: number;
  trace_id?: string | null;
  session_id?: string | null;
  question?: string | null;
  answer_preview?: string | null;
  answer_mode?: string | null;
  correction?: string | null;
  context_count?: number | null;
  sources: string[];
  status?: string;
  issue_type?: string | null;
  severity?: string | null;
  human_review_required?: boolean | null;
  triage_summary?: string | null;
  suggested_actions?: FeedbackSuggestedAction[];
  created_at: string;
  updated_at?: string | null;
};

export type FeedbackListResponse = {
  items: FeedbackItem[];
  total: number;
  limit: number;
  offset: number;
};
