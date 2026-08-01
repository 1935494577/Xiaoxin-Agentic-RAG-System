// ===== UI Config =====
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
  conversation_condense_enabled?: boolean;
  history_prune_enabled?: boolean;
  history_prune_min_similarity?: number;
  history_prune_max_turns?: number;
  history_assistant_max_chars?: number;
  chat_routing_tier?: string;
  routing_model?: string;
  condense_llm_enabled?: boolean;
  rolling_summary_every_n_turns?: number;
  rolling_summary_min_chars?: number;
  ingest_tag_presets?: string[];
  supported_upload_extensions?: string[];
  supported_upload_label?: string;
  active_persona_id?: string;
  active_persona_label?: string;
  agent_reasoning_mode?: string;
  agent_reasoning_mode_label?: string;
  rag_arch_router_enabled?: boolean;
  rag_arch_llm_fallback?: boolean;
  default_rag_architecture?: string;
  graph_extraction_enabled?: boolean;
  agentic_max_turns?: number;
  agentic_max_kb_searches?: number;
  scene_preset?: string;
  scene_presets?: Array<{ id: string; label: string; description?: string }>;
  default_assistant_mode?: "knowledge" | "task" | "auto";
};

// ===== Chat =====
export type ChatSession = {
  id: string;
  title: string;
  updated_at?: string;
};

export type UserProfile = {
  user_id: string;
  display_name: string;
  avatar_url: string;
  department: string;
  ai_display_name: string;
  ai_avatar_url: string;
  updated_at?: string;
};

export type UserProfileUpdate = {
  user_id: string;
  display_name?: string;
  avatar_url?: string;
  department?: string;
  ai_display_name?: string;
  ai_avatar_url?: string;
};

export type ToolTraceItem = {
  tool: string;
  arguments?: Record<string, unknown>;
  output?: string;
  ok?: boolean;
};

export type GraphVizNode = {
  id: string;
  label: string;
  type?: string;
  title?: string;
  department?: string;
  bio?: string;
};

export type GraphVizEdge = {
  from: string;
  to: string;
  from_label: string;
  to_label: string;
  label: string;
};

export type GraphViz = {
  center_id: string;
  nodes: GraphVizNode[];
  edges: GraphVizEdge[];
  summary_lines?: string[];
};

export type AuthUserPublic = {
  id: string;
  username: string;
  tenant_id?: string;
  department: string;
  display_name: string;
};

export type LoginResponse = {
  token: string;
  user: AuthUserPublic;
};

export type ExecutionSummary = {
  steps: number;
  tools_used: string[];
  rag_architecture?: string;
  answer_mode?: string;
  assistant_mode?: string;
};

export type ExecutionStepKind = "status" | "tool";

export type ExecutionStep = {
  id: string;
  kind: ExecutionStepKind;
  label: string;
  detail?: string;
  pending?: boolean;
  ok?: boolean;
  tool?: string;
  output?: string;
  arguments?: Record<string, unknown>;
  phase?: string;
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
    graph_viz?: GraphViz;
    rag_architecture?: string;
    assistant_mode?: string;
    execution_summary?: ExecutionSummary;
    ui_blocks?: Array<{
      type: string;
      source_paper_id?: string;
      paper_id?: string;
      title?: string;
      items?: Array<{
        id?: string;
        title?: string;
        source_filename?: string;
        question_count?: number;
      }>;
    }>;
  };
};

export type ClarifyOption = {
  id: string;
  label: string;
  hint?: string;
  output_schema_id?: string | null;
};

export type StreamEvent =
  | {
      type: "status";
      phase: string;
      answer_mode?: string;
      rag_architecture?: string;
      input_mode?: string;
      doc_task_type?: string;
      assistant_mode?: string;
      trace_id?: string;
    }
  | { type: "stream_reset" }
  | { type: "token"; content: string }
  | { type: "tool_call"; tool: string; arguments: Record<string, unknown> }
  | { type: "tool_result"; tool: string; output: string; ok: boolean }
  | { type: "graph_viz"; graph: GraphViz }
  | {
      type: "clarify";
      prompt: string;
      channel?: string;
      options: ClarifyOption[];
    }
  | { type: "error"; message: string; trace_id?: string }
  | {
      type: "done";
      answer: string;
      needs_clarify?: boolean;
      rewritten_query?: string;
      sources?: string[];
      source_refs?: Array<{ source?: string; parent_id?: string; department?: string }>;
      answer_mode?: string;
      rag_architecture?: string;
      input_mode?: string;
      verified?: boolean;
      assistant_mode?: string;
      trace_id?: string;
      tool_trace?: ToolTraceItem[];
      graph_viz?: GraphViz;
      topic_shift?: boolean;
      retrieval_query?: string;
      routing_model?: string;
      chat_routing_tier?: string;
      condense_used_llm?: boolean;
      ui_blocks?: Array<{
        type: string;
        source_paper_id?: string;
        paper_id?: string;
        title?: string;
        items?: Array<{
          id?: string;
          title?: string;
          source_filename?: string;
          question_count?: number;
        }>;
      }>;
    };

export type StreamPayload = {
  message: string;
  user_id?: string;
  user_department?: string;
  hybrid_expert_mode?: boolean;
  stream_fast_mode?: boolean;
  skip_query_rewrite?: boolean;
  session_id?: string;
  history?: Array<{ role: string; content: string }>;
  reset_context?: boolean;
  rag_architecture?: "auto" | "classic" | "graph" | "agentic";
  input_mode?: "question" | "temp_document" | "doc_task";
  doc_task_type?: "summary" | "compare" | "extract" | "annotate";
  temp_document_id?: string;
  allowed_sources?: string[] | null;
  scenario_tags?: string[];
  channel?: "wecom" | "wechat" | "miniprogram" | "channels" | "douyin";
  output_schema_id?: string;
  skip_clarify?: boolean;
  clarify_choice_id?: string;
  assistant_mode?: "knowledge" | "task" | "auto";
};

export type IngestedSource = {
  source: string;
  parent_count: number;
  child_count: number;
};

export type EphemeralDoc = {
  doc_id: string;
  filename: string;
  session_id: string;
};

// ===== Model Profiles =====
export type ModelProfile = {
  id: string;
  name: string;
  vendor: string;
  api_base?: string;
  api_path?: string;
  default_model?: string;
  routing_model?: string;
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
export type PersonaPreset = {
  id: string;
  label: string;
  description: string;
  content?: string;
};

export type ReasoningModeOption = {
  id: string;
  label: string;
  description: string;
};

export type PromptSlot = {
  id: string;
  label: string;
  scope: string[];
  category: string;
  builtin: boolean;
  enabled: boolean;
  order: number;
  template: string;
  content?: string;
  description?: string;
};

export type PromptData = {
  mode?: string;
  active_persona_id?: string;
  persona_presets?: PersonaPreset[];
  agent_reasoning_mode?: string;
  reasoning_modes?: ReasoningModeOption[];
  slots: PromptSlot[];
  composite?: string;
  preview?: { composed?: string; layers?: Array<{ label: string; category: string; content: string }> };
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

export type FeedbackStats = {
  since_days: number;
  tenant_id: string;
  total: number;
  positive: number;
  negative: number;
  pending_triage: number;
  by_issue_type: Array<{ issue_type: string; count: number }>;
  by_status: Array<{ status: string; count: number }>;
};

export type SourcePreview = {
  parent_id: string;
  source: string;
  department: string;
  permission_label: string;
  text: string;
};

export type ScenarioCatalogItem = {
  id: string;
  label: string;
  department: string[];
  channel: string | null;
  channel_label: string;
  user_goal: string;
  steps: string[];
  scene_preset: string | null;
  clarify_option_id: string | null;
  output_schema_id: string | null;
  tools: string[];
  tech_setup?: string;
  tech?: Record<string, unknown>;
};

export type ScenarioCatalogResponse = {
  title: string;
  department: string;
  department_info: {
    label?: string;
    summary?: string;
    admin_features?: string[];
    default_scene_preset?: string;
    chat_channels?: string[];
    chat_note?: string;
  } | null;
  chat_note?: string;
  show_tech: boolean;
  scenarios: ScenarioCatalogItem[];
  departments: Record<string, { label?: string; summary?: string }>;
};
