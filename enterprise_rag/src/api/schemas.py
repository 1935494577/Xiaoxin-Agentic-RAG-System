from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatHistoryTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=16000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    user_id: str = Field(..., min_length=1, max_length=128)
    user_department: str = Field(default="general", max_length=64)
    allowed_sources: list[str] | None = None
    session_id: str | None = Field(default=None, max_length=64, description="用于加载长期会话记忆")
    history: list[ChatHistoryTurn] | None = Field(
        default=None,
        description="可选：客户端提供的短期历史；未提供时从 session_id 加载",
    )
    reset_context: bool = Field(
        default=False,
        description="为 true 时视为新话题：忽略 history、清空会话滚动摘要",
    )
    # 已保存的模型配置 id；与 force_env_llm 互斥优先级：force_env_llm 为真时仅用 .env
    model_profile_id: str | None = Field(default=None, max_length=64)
    force_env_llm: bool = False
    # OpenAI 兼容：覆盖配置中的 default_model
    chat_model: str | None = Field(default=None, max_length=128)
    temperature: float | None = Field(default=None, ge=0, le=2, description="生成温度")
    verifier_temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens_rewrite: int | None = Field(default=None, ge=1, le=4096)
    max_tokens_answer: int | None = Field(default=None, ge=1, le=128000)
    max_tokens_verifier: int | None = Field(default=None, ge=1, le=4096)
    skip_query_rewrite: bool | None = Field(
        default=None,
        description="为 true 时跳过 LLM 查询改写；None 时使用服务端 query_rewrite_enabled 配置",
    )
    routing_model: str | None = Field(
        default=None,
        max_length=128,
        description="预处理专用模型（condense/kb judge/摘要）；None 时用 UI/配置默认值",
    )
    stream_fast_mode: bool | None = Field(
        default=None,
        description="内部快速检索路径；None 使用 UI 配置 stream_fast_mode",
    )
    hybrid_expert_mode: bool | None = Field(
        default=None,
        description="混合专家模式：true=RAG 未命中可走通用；false=仅 RAG；None 使用 UI 默认",
    )


class SourceRef(BaseModel):
    source: str = ""
    parent_id: str = ""
    department: str = ""
    permission_label: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    rewritten_query: str | None = None
    answer_mode: str | None = None
    verified: bool | None = None


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    user_department: str = Field(default="general", max_length=64)
    top_k: int = Field(default=5, ge=1, le=20)
    allowed_sources: list[str] | None = None
    retrieval_dedup: bool | None = None


class RetrieveHit(BaseModel):
    parent_id: str
    source: str = ""
    department: str = ""
    permission_label: str = ""
    hybrid_score: float | None = None
    rerank_score: float | None = None
    text: str


class RetrieveResponse(BaseModel):
    rewritten_query: str
    hits: list[RetrieveHit] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    message_id: str | None = Field(default=None, max_length=128, description="兼容旧客户端，等同 trace_id")
    trace_id: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, max_length=64)
    question: str | None = Field(default=None, max_length=8000)
    answer_preview: str | None = Field(default=None, max_length=4000)
    answer_mode: str | None = Field(default=None, max_length=64)
    rating: int = Field(..., ge=-1, le=1)
    correction: str | None = Field(default=None, max_length=4000)


class FeedbackSuggestedAction(BaseModel):
    action: str = ""
    confidence: float | None = None
    detail: str | None = None


class FeedbackPublic(BaseModel):
    id: str
    tenant_id: str = "internal"
    user_id: str
    rating: int
    trace_id: str | None = None
    session_id: str | None = None
    message_id: str | None = None
    question: str | None = None
    answer_preview: str | None = None
    answer_mode: str | None = None
    correction: str | None = None
    context_count: int | None = None
    sources: list[str] = Field(default_factory=list)
    status: str = "pending"
    issue_type: str | None = None
    severity: str | None = None
    human_review_required: bool | None = None
    triage_summary: str | None = None
    suggested_actions: list[FeedbackSuggestedAction] = Field(default_factory=list)
    created_at: str
    updated_at: str | None = None


class FeedbackListResponse(BaseModel):
    items: list[FeedbackPublic]
    total: int
    limit: int
    offset: int


class FeedbackTriageRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=50)
    use_llm: bool = True
    rating: int | None = Field(default=None, ge=-1, le=1)


class FeedbackTriageResponse(BaseModel):
    processed: int
    failed: int
    queued: int


class FeedbackActionResult(BaseModel):
    action: str = ""
    ok: bool = False
    skipped: bool | None = None
    reason: str | None = None
    error: str | None = None
    revision_id: str | None = None
    proposal_id: str | None = None
    golden_path: str | None = None


class FeedbackStatusResponse(BaseModel):
    id: str
    status: str
    issue_type: str | None = None
    severity: str | None = None
    triage_summary: str | None = None
    action_results: list[FeedbackActionResult] = Field(default_factory=list)


class ConfigRevisionPublic(BaseModel):
    id: str
    created_at: str
    feedback_id: str
    tenant_id: str = "internal"
    action: str
    patch: dict[str, Any] = Field(default_factory=dict)
    rolled_back: bool = False
    rolled_back_at: str | None = None
    diff: dict[str, Any] = Field(default_factory=dict)


class ConfigRevisionListResponse(BaseModel):
    items: list[ConfigRevisionPublic]
    total: int
    limit: int
    offset: int


class FeedbackEvaluateRequest(BaseModel):
    feedback_id: str | None = Field(default=None, max_length=64)
    revision_id: str | None = Field(default=None, max_length=64)


class FeedbackEvaluateResponse(BaseModel):
    ok: bool
    report_id: str | None = None
    feedback_id: str | None = None
    revision_id: str | None = None
    golden_rows: int = 0
    mode: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    delta: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: str | None = None


class EvalReportPublic(BaseModel):
    id: str
    created_at: str
    feedback_id: str | None = None
    revision_id: str | None = None
    golden_rows: int = 0
    mode: str = "fallback_naive"
    metrics: dict[str, Any] = Field(default_factory=dict)
    baseline_metrics: dict[str, Any] = Field(default_factory=dict)
    delta: dict[str, Any] = Field(default_factory=dict)


class EvalReportListResponse(BaseModel):
    items: list[EvalReportPublic]
    total: int
    limit: int
    offset: int


class IngestDedupStatsResponse(BaseModel):
    content_hash: str | None = None
    doc_duplicate: bool = False
    canonical_source: str | None = None
    alias_sources: list[str] = Field(default_factory=list)
    skipped_parents: int = 0
    skipped_children: int = 0
    indexed_parents: int = 0
    indexed_children: int = 0


class IngestResponse(BaseModel):
    chunks_indexed: int
    source: str
    tags: list[str] = Field(default_factory=list)
    ingest_mode: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    router: str | None = None
    file_type: str | None = None
    message: str | None = None
    dedup: IngestDedupStatsResponse | None = None


class PreviewRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000_000)
    use_presidio: bool = True


class PreviewResponse(BaseModel):
    cleaned: str


class IngestTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000_000)
    source: str = Field(default="paste.txt", max_length=256)
    department: str | None = Field(default=None, max_length=64)
    permission_label: str | None = Field(default=None, max_length=64)
    tags: list[str] = Field(default_factory=list, max_length=20)
    use_presidio: bool = True


class PublicConfigResponse(BaseModel):
    embedding_model: str
    reranker_model: str
    default_chat_model: str
    use_presidio_default: bool


class ModelProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    vendor: str = Field(default="custom", max_length=64)
    api_base: str = Field(..., min_length=1, max_length=512, description="如 https://api.deepseek.com")
    api_path: str | None = Field(default=None, max_length=256, description="可选，如 /compatible-mode/v1")
    default_model: str = Field(..., min_length=1, max_length=128)
    routing_model: str | None = Field(
        default=None,
        max_length=128,
        description="预处理用小模型；留空则与 default_model 相同",
    )
    api_key: str = Field(default="", max_length=2048)
    extra_headers: dict[str, str] | None = None


class ModelProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    vendor: str | None = Field(default=None, max_length=64)
    api_base: str | None = Field(default=None, max_length=512)
    api_path: str | None = Field(default=None, max_length=256)
    default_model: str | None = Field(default=None, max_length=128)
    routing_model: str | None = Field(default=None, max_length=128)
    api_key: str | None = Field(default=None, max_length=2048)
    extra_headers: dict[str, str] | None = None


class ModelProfilePublic(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    vendor: str
    api_base: str
    api_path: str | None = None
    combined_base: str = ""
    default_model: str
    routing_model: str = ""
    has_api_key: bool
    api_key_hint: str = ""
    extra_headers: dict[str, str] = Field(default_factory=dict)


class ModelProfileListResponse(BaseModel):
    profiles: list[ModelProfilePublic]
    default_profile_id: str | None = None


class ModelProfileTestRequest(BaseModel):
    api_base: str = Field(..., min_length=1, max_length=512)
    api_path: str | None = Field(default=None, max_length=256)
    default_model: str = Field(..., min_length=1, max_length=128)
    api_key: str = Field(..., min_length=1, max_length=2048)
    extra_headers: dict[str, str] | None = None


class ModelConnectionStatus(BaseModel):
    connected: bool
    message: str = ""


class UiConfigPublic(BaseModel):
    logo_en: str = "JNAO"
    logo_cn: str = "劲脑"
    logo_image_path: str = ""
    has_logo_image: bool = False
    app_title: str = "入库小帮手"
    app_tagline: str = ""
    suggested_questions: list[str] = Field(default_factory=list)
    supported_upload_extensions: list[str] = Field(default_factory=list)
    supported_upload_label: str = ""
    stream_fast_mode: bool = True
    max_history_turns: int = 6
    max_history_chars: int = 6000
    kb_min_score: float = 0.55
    kb_min_rerank_score: float = 0.0
    kb_llm_judge: bool = True
    general_fallback_enabled: bool = False
    kb_post_stream_fallback: bool = False
    hybrid_expert_mode: bool = False
    stream_verifier_enabled: bool = False
    graph_verifier_enabled: bool = False
    long_term_memory_enabled: bool = True
    routing_model: str = ""
    chat_routing_tier: str = "balanced"
    condense_llm_enabled: bool = True
    kb_llm_judge_always: bool = False
    ingest_tag_presets: list[str] = Field(default_factory=list)


class UiConfigUpdate(BaseModel):
    logo_en: str | None = Field(default=None, max_length=64)
    logo_cn: str | None = Field(default=None, max_length=64)
    app_title: str | None = Field(default=None, max_length=128)
    app_tagline: str | None = Field(default=None, max_length=512)
    suggested_questions: list[str] | None = None
    clear_logo_image: bool = False
    stream_fast_mode: bool | None = None
    max_history_turns: int | None = Field(default=None, ge=1, le=50)
    max_history_chars: int | None = Field(default=None, ge=500, le=100000)
    kb_min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    kb_min_rerank_score: float | None = None
    kb_llm_judge: bool | None = None
    general_fallback_enabled: bool | None = None
    kb_post_stream_fallback: bool | None = None
    hybrid_expert_mode: bool | None = None
    stream_verifier_enabled: bool | None = None
    graph_verifier_enabled: bool | None = None
    long_term_memory_enabled: bool | None = None
    routing_model: str | None = Field(default=None, max_length=128)
    chat_routing_tier: str | None = Field(default=None, pattern="^(fast|balanced|quality)$")
    condense_llm_enabled: bool | None = None
    kb_llm_judge_always: bool | None = None
    conversation_condense_enabled: bool | None = None
    history_prune_enabled: bool | None = None
    history_prune_min_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    history_prune_max_turns: int | None = Field(default=None, ge=1, le=20)
    history_assistant_max_chars: int | None = Field(default=None, ge=100, le=8000)
    rolling_summary_enabled: bool | None = None
    rolling_summary_every_n_turns: int | None = Field(default=None, ge=2, le=30)
    rolling_summary_min_chars: int | None = Field(default=None, ge=500, le=100000)
    ingest_tag_presets: list[str] | None = None


class ProcessingToolPublic(BaseModel):
    id: str
    label: str
    enabled: bool = True


class ProcessingToolsPublic(BaseModel):
    use_llm_router: bool = True
    tools: list[ProcessingToolPublic] = Field(default_factory=list)
    extension_map: dict[str, str] = Field(default_factory=dict)


class ProcessingToolsUpdate(BaseModel):
    use_llm_router: bool | None = None
    tools: dict[str, dict[str, Any]] | None = None


class PromptSlotPublic(BaseModel):
    id: str
    label: str
    description: str = ""
    category: str = "custom"
    scope: list[str] = Field(default_factory=lambda: ["all"])
    enabled: bool = True
    order: int = 100
    content: str = ""
    builtin: bool = False
    variant: str | None = None


class PromptPreviewPublic(BaseModel):
    mode: str
    fast: bool = False
    layers: list[dict[str, str]] = Field(default_factory=list)
    composed: str = ""


class PromptConfigPublic(BaseModel):
    version: int = 1
    slots: list[PromptSlotPublic] = Field(default_factory=list)
    categories: dict[str, str] = Field(default_factory=dict)
    preview: PromptPreviewPublic | None = None


class PromptSlotUpdate(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    label: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=256)
    category: str | None = Field(default=None, max_length=32)
    scope: list[str] | None = None
    enabled: bool | None = None
    order: int | None = Field(default=None, ge=0, le=9999)
    content: str | None = Field(default=None, max_length=8000)
    variant: str | None = Field(default=None, max_length=16)


class PromptConfigUpdate(BaseModel):
    slots: list[PromptSlotUpdate] | None = None
    reset_defaults: bool = False


class ChatSessionPublic(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class ChatSessionCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    title: str = Field(default="新对话", max_length=128)


class ChatSessionUpdate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=128)


class ChatMessagePublic(BaseModel):
    role: str
    content: str
    meta: dict[str, Any] | None = None


class ChatMessagesAppend(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    messages: list[ChatMessagePublic] = Field(..., min_length=1, max_length=50)
    auto_title_from: str | None = Field(default=None, max_length=80)


class VectorStorePublic(BaseModel):
    id: str
    name: str
    backend: str
    backend_label: str = ""
    embedding_model: str = ""
    embedding_dim: int | None = None
    numpy_path: str = ""
    bm25_path: str = ""
    milvus_collection: str = ""
    vector_count: int = 0
    bm25_docs: int = 0
    compatible: bool = True
    current_embedding_model: str = ""
    current_embedding_dim: int | None = None
    active: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class VectorStoreBackendOption(BaseModel):
    id: str
    label: str
    available: bool = True


class VectorStoreListResponse(BaseModel):
    stores: list[VectorStorePublic] = Field(default_factory=list)
    active_store_id: str | None = None
    active: VectorStorePublic | None = None
    available_backends: list[VectorStoreBackendOption] = Field(default_factory=list)


class VectorStoreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    backend: str = Field(default="numpy", max_length=32)
