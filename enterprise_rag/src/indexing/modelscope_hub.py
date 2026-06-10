"""可选：通过魔搭 ModelScope 拉取模型到本地目录，再交给 FlagEmbedding / Transformers 加载（国内网络友好）。"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_WEIGHT_MARKERS = (
    "pytorch_model.bin",
    "model.safetensors",
    "config.json",
)


def _apply_modelscope_env() -> None:
    """Windows 默认无符号链接权限；禁用魔搭 symlink 可避免 WARNING 并保证路径一致。"""
    if os.name == "nt":
        os.environ.setdefault("MODELSCOPE_SYMLINK_FILES_IN_ROOT_ENABLED", "false")
        os.environ.setdefault("MODELSCOPE_SYMLINK", "0")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


_apply_modelscope_env()


def default_modelscope_cache_dir() -> Path:
    """enterprise_rag/data/models"""
    return Path(__file__).resolve().parents[2] / "data" / "models"


def _cache_root() -> Path:
    from config import settings

    raw = (settings.modelscope_cache_dir or "").strip()
    root = Path(raw).expanduser().resolve() if raw else default_modelscope_cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _ms_escape_segment(name: str) -> str:
    """ModelScope cache dir: dots in repo name become triple underscores."""
    return name.replace(".", "___")


def _dir_has_weights(path: Path) -> bool:
    return path.is_dir() and any((path / name).is_file() for name in _WEIGHT_MARKERS)


def _candidate_dirs(model_id: str) -> list[Path]:
    """Canonical id path plus ModelScope escaped folder (e.g. v1.5 -> v1___5)."""
    mid = model_id.strip()
    if not mid:
        return []
    root = _cache_root()
    parts = mid.split("/")
    out: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        key = str(p.resolve()) if p.exists() else str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)

    add(root.joinpath(*parts))
    if parts:
        escaped = [*parts[:-1], _ms_escape_segment(parts[-1])] if len(parts) > 1 else [_ms_escape_segment(parts[0])]
        add(root.joinpath(*escaped))
    return out


def _pick_weight_dir(model_id: str) -> Path | None:
    for candidate in _candidate_dirs(model_id):
        if _dir_has_weights(candidate):
            return candidate
    return None


def _ensure_canonical_alias(model_id: str, actual: Path) -> Path:
    """When symlink fails on Windows, copy/junction is heavy; return actual dir."""
    canonical = _candidate_dirs(model_id)[0]
    if actual.resolve() == canonical.resolve():
        return actual
    if _dir_has_weights(canonical):
        return canonical
    if os.name != "nt" or canonical.exists():
        return actual
    try:
        os.symlink(actual, canonical, target_is_directory=True)
        if _dir_has_weights(canonical):
            return canonical
    except OSError:
        logger.debug("ModelScope symlink unavailable for %s -> %s", actual, canonical)
    return actual


def local_model_dir(model_id: str) -> Path | None:
    """Return local model directory when weights already exist on disk."""
    return _pick_weight_dir(model_id)


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
    _apply_modelscope_env()
    mid = model_id.strip()
    if not mid:
        raise ValueError("model_id is empty")

    existing = local_model_dir(mid)
    if existing is not None:
        return str(existing)

    if not download_if_missing:
        escaped_hint = ""
        if "." in mid.split("/")[-1]:
            escaped_hint = f" (ModelScope may use {_ms_escape_segment(mid.split('/')[-1])})"
        raise FileNotFoundError(
            f"Local model not found for {mid!r}{escaped_hint}. "
            "Run scripts/download_rag_models.py or restart API after models are cached."
        )

    try:
        from modelscope.hub.snapshot_download import snapshot_download
    except ImportError as e:
        raise ImportError("使用 ModelScope 下载需安装：pip install modelscope") from e

    downloaded = Path(snapshot_download(mid, cache_dir=str(_cache_root())))
    resolved = _pick_weight_dir(mid)
    if resolved is not None:
        return str(_ensure_canonical_alias(mid, resolved))
    if _dir_has_weights(downloaded):
        return str(_ensure_canonical_alias(mid, downloaded))
    raise FileNotFoundError(f"ModelScope download finished but weights missing for {mid!r}")
