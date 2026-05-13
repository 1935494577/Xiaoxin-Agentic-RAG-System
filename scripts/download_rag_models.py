#!/usr/bin/env python3
"""从 Hugging Face Hub 预下载嵌入与重排模型（写入 HF_HUB_CACHE 或默认缓存）。

在仓库根目录执行: python scripts/download_rag_models.py

若 `.env` 中 `USE_MODELSCOPE_DOWNLOAD=true`，嵌入与 Flag 重排会在 API 首次加载时经魔搭下载，一般不必再运行本脚本；
仅当你仍需要从 Hub 预拉权重（例如调试 HF 缓存）时，可暂时关闭该开关后执行。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
sys.path.insert(0, str(SRC))

from huggingface_hub import snapshot_download  # noqa: E402

from config import settings  # noqa: E402


def _hf_cache_dir_str() -> str | None:
    raw = (settings.hf_hub_cache or "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def _hub_ids() -> list[str]:
    out: list[str] = []
    for raw in (settings.embedding_model, settings.reranker_model):
        s = str(raw).strip()
        if not s or "/" not in s:
            continue
        p = Path(s)
        if p.exists() and p.is_dir():
            continue
        out.append(s)
    return out


def main() -> None:
    if settings.use_modelscope_download:
        print(
            "已启用 USE_MODELSCOPE_DOWNLOAD：Flag 嵌入与重排走魔搭 ModelScope，无需运行本 HF 预下载脚本。\n"
            "若仍需从 Hub 预拉，请将该变量设为 false 后重试。"
        )
        return
    cache = _hf_cache_dir_str()
    for repo_id in _hub_ids():
        print(f"Downloading {repo_id!r} ...")
        snapshot_download(
            repo_id,
            cache_dir=cache,
            resume_download=True,
        )
        print(f"  done: {repo_id}")


if __name__ == "__main__":
    main()
