import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root (contains docker-compose, Makefile)
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    milvus_host: str = "127.0.0.1"
    milvus_port: int = 19530
    use_milvus_lite: bool = True
    milvus_lite_data_dir: Path = _REPO_ROOT / "enterprise_rag" / "data" / "milvus_lite"
    bm25_index_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "bm25_index.json"
    numpy_vector_store_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "numpy_vectors.json"
    vector_stores_registry_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "vector_stores.json"
    vector_stores_data_dir: Path = _REPO_ROOT / "enterprise_rag" / "data" / "vector_stores"

    elasticsearch_url: str = "http://localhost:9200"

    # Optional Redis: hybrid search result cache (TTL + connection pool)
    redis_url: str = ""
    redis_search_cache_enabled: bool = True
    redis_search_cache_ttl_seconds: int = 300

    openai_api_base: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"

    embedding_model: str = "BAAI/bge-m3"
    # embedding_backend=auto 且 Flag 加载失败时，sentence-transformers 回退用（勿填 bge-m3，ST 无法按单塔加载）
    embedding_st_fallback: str = "BAAI/bge-small-zh-v1.5"
    reranker_model: str = "BAAI/bge-reranker-base"

    milvus_collection: str = "enterprise_rag_child_chunks"
    es_parent_index: str = "enterprise_rag_parents"

    data_raw_dir: Path = _REPO_ROOT / "enterprise_rag" / "data" / "raw"
    data_processed_dir: Path = _REPO_ROOT / "enterprise_rag" / "data" / "processed"
    data_chunks_dir: Path = _REPO_ROOT / "enterprise_rag" / "data" / "chunks"
    data_feedback_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "feedback.jsonl"
    chat_sessions_db_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "chat_sessions.db"
    chat_trace_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "chat_trace.jsonl"
    model_profiles_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "model_profiles.json"
    ui_config_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "ui_config.json"
    prompt_config_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "prompt_config.json"
    processing_tools_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "processing_tools.json"
    agent_tools_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "agent_tools.json"
    doc_registry_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "doc_registry.json"
    chunk_dedup_index_path: Path = _REPO_ROOT / "enterprise_rag" / "data" / "chunk_dedup_index.json"
    ui_branding_dir: Path = _REPO_ROOT / "enterprise_rag" / "data" / "branding"

    # L1/L2 ingest dedup
    ingest_content_hash_enabled: bool = True
    ingest_chunk_dedup_enabled: bool = True
    ingest_chunk_simhash_max_hamming: int = 3

    # L3 retrieval dedup
    retrieval_dedup_enabled: bool = True
    retrieval_dedup_similarity: float = 0.88
    retrieval_mmr_lambda: float = 0.72

    parent_chunk_size: int = 1000
    parent_chunk_overlap: int = 200
    child_chunk_size: int = 200
    child_chunk_overlap: int = 50

    hybrid_vector_weight: float = 0.6
    hybrid_bm25_weight: float = 0.4
    retrieve_top_k: int = 20
    rerank_top_k: int = 5
    # 流式对话 — 快速模式参数（stream_fast_mode=true 时启用）
    stream_standard_retrieve_top_k: int = 10
    stream_retrieve_top_k: int = 6
    stream_rerank_top_k: int = 3
    stream_skip_rerank: bool = True
    stream_pre_rerank_k: int = 6
    stream_context_max_chars: int = 700
    # 为 false 时跳过 LLM 查询改写，显著降低首 token 延迟
    query_rewrite_enabled: bool = False

    use_presidio: bool = True
    default_department: str = "技术部"
    default_permission_label: str = "public"

    llama_cloud_api_key: str = ""

    torch_device: str = "auto"
    use_fp16: bool = True
    embedding_batch_size: int = 8
    # 为 false 时启动只预热嵌入模型（流式+跳过重排时可省 ~500MB）
    warmup_reranker_on_startup: bool = True
    # 为 false 时跳过启动线程中的模型下载/预热（首请求会冷启动）
    warmup_models_on_startup: bool = True

    hf_endpoint: str = ""
    http_proxy: str = ""
    https_proxy: str = ""
    # 非空时写入 HF_HUB_CACHE，模型统一落盘到大盘；便于拷贝备份
    hf_hub_cache: str = ""
    # 仅使用本地已缓存文件（拷完模型后开启，避免联网）
    hf_local_files_only: bool = False
    # auto：先 Flag 再 sentence-transformers；flag / sentence_transformers：固定一路（弱网可先 ST + 小模型）
    embedding_backend: str = "auto"
    # auto：先 FlagReranker 再 CrossEncoder；flag / cross_encoder：固定一路
    reranker_backend: str = "auto"

    # 为 true 时嵌入与重排模型均优先经 ModelScope 下载到本地再加载（需 pip install modelscope）
    use_modelscope_download: bool = False
    # 留空则使用 enterprise_rag/data/models
    modelscope_cache_dir: str = ""

    rag_api_secret: str = ""
    cors_allow_origins: str = ""
    disable_openapi_docs: bool = False
    trusted_hosts: str = ""
    enable_hsts: bool = False

    # LangSmith / LangChain：写入进程环境，供 `configure_tracing` 与 LangChain 库读取（与 .env 中 LANGCHAIN_* 对应）
    langchain_tracing_v2: bool = Field(default=False, validation_alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field(default="", validation_alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="", validation_alias="LANGCHAIN_PROJECT")
    # 本地 JSONL 链路 trace（第三步写入；此处仅控制状态展示与后续开关）
    local_trace_enabled: bool = Field(default=False, validation_alias="LOCAL_TRACE_ENABLED")


# `.env` 优先：避免 shell 中残留的 LANGCHAIN_* 覆盖项目配置
for _lang_key in ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT", "LOCAL_TRACE_ENABLED"):
    os.environ.pop(_lang_key, None)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

_hf = (settings.hf_endpoint or os.environ.get("HF_ENDPOINT", "") or "").strip()
if _hf:
    os.environ["HF_ENDPOINT"] = _hf.rstrip("/")


def _apply_proxy_env_from_settings() -> None:
    hp = (settings.http_proxy or "").strip()
    hps = (settings.https_proxy or "").strip()
    if not hp and not hps:
        return
    if hp:
        os.environ["HTTP_PROXY"] = hp
        os.environ["http_proxy"] = hp
    if hps:
        os.environ["HTTPS_PROXY"] = hps
        os.environ["https_proxy"] = hps
    if hp and not hps:
        os.environ["HTTPS_PROXY"] = hp
        os.environ["https_proxy"] = hp
    if hps and not hp:
        os.environ["HTTP_PROXY"] = hps
        os.environ["http_proxy"] = hps


_apply_proxy_env_from_settings()


def _apply_hf_hub_cache() -> None:
    raw = (settings.hf_hub_cache or "").strip()
    if not raw:
        return
    p = Path(raw).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HUB_CACHE"] = str(p)


_apply_hf_hub_cache()


def _apply_modelscope_env() -> None:
    if os.name == "nt":
        os.environ.setdefault("MODELSCOPE_SYMLINK_FILES_IN_ROOT_ENABLED", "false")
        os.environ.setdefault("MODELSCOPE_SYMLINK", "0")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


_apply_modelscope_env()


def _apply_hf_local_files_only() -> None:
    if not settings.hf_local_files_only:
        return
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


_apply_hf_local_files_only()


def _sync_hf_hub_constants_endpoint() -> None:
    v = (os.environ.get("HF_ENDPOINT") or "").strip().rstrip("/")
    if not v:
        return
    try:
        import huggingface_hub.constants as _hfc  # noqa: PLC0415
    except ImportError:
        return
    if getattr(_hfc, "ENDPOINT", None) == v:
        return
    _hfc.ENDPOINT = v
    _hfc.HUGGINGFACE_CO_URL_TEMPLATE = v + "/{repo_id}/resolve/{revision}/{filename}"


_sync_hf_hub_constants_endpoint()


def _apply_langchain_env_from_settings() -> None:
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langchain_tracing_v2 else "false"
    key = (settings.langchain_api_key or "").strip()
    if key:
        os.environ["LANGCHAIN_API_KEY"] = key
    else:
        os.environ.pop("LANGCHAIN_API_KEY", None)
    proj = (settings.langchain_project or "").strip()
    if proj:
        os.environ["LANGCHAIN_PROJECT"] = proj
    else:
        os.environ.pop("LANGCHAIN_PROJECT", None)


_apply_langchain_env_from_settings()
