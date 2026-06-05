"""可选：通过魔搭 ModelScope 拉取模型到本地目录，再交给 FlagEmbedding / Transformers 加载（国内网络友好）。"""

from __future__ import annotations

from pathlib import Path

_WEIGHT_MARKERS = (
    "pytorch_model.bin",
    "model.safetensors",
    "config.json",
)


def default_modelscope_cache_dir() -> Path:
    """enterprise_rag/data/models"""
    return Path(__file__).resolve().parents[2] / "data" / "models"


def _cache_root() -> Path:
    from config import settings

    raw = (settings.modelscope_cache_dir or "").strip()
    root = Path(raw).expanduser().resolve() if raw else default_modelscope_cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def local_model_dir(model_id: str) -> Path | None:
    """Return local model directory when weights already exist on disk."""
    mid = model_id.strip()
    if not mid:
        return None
    root = _cache_root()
    local = root.joinpath(*mid.split("/"))
    if not local.is_dir():
        return None
    if any((local / name).is_file() for name in _WEIGHT_MARKERS):
        return local
    return None


def snapshot_model_to_local(model_id: str) -> str:
    """Download model_id to local cache if needed; return directory for from_pretrained."""
    return resolve_model_path(model_id, download_if_missing=True)


def inference_model_path(model_id: str, *, allow_download: bool | None = None) -> str:
    """加载推理用本地目录：魔搭模式下缺失则下载，已有则直接返回路径。"""
    from config import settings

    mid = model_id.strip()
    if not mid:
        raise ValueError("model_id is empty")

    existing = local_model_dir(mid)
    if existing is not None:
        return str(existing)

    if settings.use_modelscope_download:
        do_dl = allow_download if allow_download is not None else True
        return resolve_model_path(mid, download_if_missing=do_dl)

    p = Path(mid)
    if p.is_dir():
        return str(p.resolve())
    return mid


def resolve_model_path(model_id: str, *, download_if_missing: bool = True) -> str:
    """Resolve model_id to a local directory; download only when files are missing."""
    mid = model_id.strip()
    if not mid:
        raise ValueError("model_id is empty")

    existing = local_model_dir(mid)
    if existing is not None:
        return str(existing)

    if not download_if_missing:
        raise FileNotFoundError(
            f"Local model not found for {mid!r}. "
            "Run scripts/download_rag_models.py or restart API after models are cached."
        )

    try:
        from modelscope.hub.snapshot_download import snapshot_download
    except ImportError as e:
        raise ImportError("使用 ModelScope 下载需安装：pip install modelscope") from e

    return snapshot_download(mid, cache_dir=str(_cache_root()))
