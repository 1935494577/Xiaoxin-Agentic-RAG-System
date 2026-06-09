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
    stream_fast_mode: bool | None = Field(
        default=None,
        description="true=快速流式（跳过重排等）；false=标准流式；None 使用 UI 配置 stream_fast_mode",
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
    message_id: str | None = None
    rating: int = Field(..., ge=-1, le=1)
    correction: str | None = None


class IngestResponse(BaseModel):
    chunks_indexed: int
    source: str
    ingest_mode: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    router: str | None = None
    file_type: str | None = None
    message: str | None = None


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
    api_key: str = Field(default="", max_length=2048)
    extra_headers: dict[str, str] | None = None


class ModelProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    vendor: str | None = Field(default=None, max_length=64)
    api_base: str | None = Field(default=None, max_length=512)
    api_path: str | None = Field(default=None, max_length=256)
    default_model: str | None = Field(default=None, max_length=128)
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
    app_title: str = "企业知识库助手"
    app_tagline: str = ""
    suggested_questions: list[str] = Field(default_factory=list)
    supported_upload_extensions: list[str] = Field(default_factory=list)
    supported_upload_label: str = ""
    stream_fast_mode: bool = False
    max_history_turns: int = 6
    max_history_chars: int = 6000
    kb_min_score: float = 0.55
    kb_min_rerank_score: float = 0.0
    kb_llm_judge: bool = True
    general_fallback_enabled: bool = True
    stream_verifier_enabled: bool = True
    long_term_memory_enabled: bool = True


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
    stream_verifier_enabled: bool | None = None
    long_term_memory_enabled: bool | None = None


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
