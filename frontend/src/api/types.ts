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
  };
};

export type StreamEvent =
  | { type: "status"; phase: string; answer_mode?: string; trace_id?: string }
  | { type: "stream_reset" }
  | { type: "token"; content: string }
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
  use_hybrid_expert_router: boolean;
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
};
