"""可选：通过魔搭 ModelScope 拉取模型到本地目录，再交给 FlagEmbedding / Transformers 加载（国内网络友好）。"""

from __future__ import annotations

from pathlib import Path


def default_modelscope_cache_dir() -> Path:
    """enterprise_rag/data/models"""
    return Path(__file__).resolve().parents[2] / "data" / "models"


def snapshot_model_to_local(model_id: str) -> str:
    """将 model_id 下载到本地，返回可供 from_pretrained 使用的目录路径。"""
    from config import settings

    try:
        from modelscope.hub.snapshot_download import snapshot_download
    except ImportError as e:
        raise ImportError(
            "使用 ModelScope 下载需安装：pip install modelscope"
        ) from e

    raw = (settings.modelscope_cache_dir or "").strip()
    root = Path(raw).expanduser().resolve() if raw else default_modelscope_cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    return snapshot_download(model_id.strip(), cache_dir=str(root))
