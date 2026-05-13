from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    user_id: str = Field(..., min_length=1, max_length=128)
    user_department: str = Field(default="general", max_length=64)
    allowed_sources: list[str] | None = None
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


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    rewritten_query: str | None = None


class FeedbackRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    message_id: str | None = None
    rating: int = Field(..., ge=-1, le=1)
    correction: str | None = None


class IngestResponse(BaseModel):
    chunks_indexed: int
    source: str


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
