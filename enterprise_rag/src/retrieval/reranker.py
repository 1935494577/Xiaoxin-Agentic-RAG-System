from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from config import settings
from runtime_device import use_fp16_safe, torch_device_string


def _hf_cache_dir() -> str | None:
    raw = (settings.hf_hub_cache or "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def _ce_local_kw() -> dict[str, Any]:
    kw: dict[str, Any] = {"trust_remote_code": True}
    cd = _hf_cache_dir()
    if cd:
        kw["cache_folder"] = cd
    if settings.hf_local_files_only:
        kw["local_files_only"] = True
    return kw


@lru_cache
def _flag_reranker():
    from FlagEmbedding import FlagAutoReranker

    model_path = settings.reranker_model
    if settings.use_modelscope_download:
        from indexing.modelscope_hub import snapshot_model_to_local

        model_path = snapshot_model_to_local(settings.reranker_model)

    kw: dict[str, Any] = {
        "model_name_or_path": model_path,
        "use_fp16": use_fp16_safe(),
        "trust_remote_code": True,
    }
    cd = _hf_cache_dir()
    if cd:
        kw["cache_dir"] = cd
    return FlagAutoReranker.from_finetuned(**kw)


@lru_cache
def _cross_encoder():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(
        settings.reranker_model,
        device=torch_device_string(),
        **_ce_local_kw(),
    )


def rerank_parents(question: str, items: list[dict[str, Any]], top_k: int | None = None) -> list[dict[str, Any]]:
    """重排：auto 时先 Flag 再 CrossEncoder；可配置仅 CrossEncoder 降低显存与下载体积。"""
    if not items:
        return []
    k = top_k or settings.rerank_top_k
    pairs = [[question, (it.get("text") or "")] for it in items]

    def _scores_to_list(scores) -> list[float]:
        if isinstance(scores, (int, float)):
            return [float(scores)]
        if hasattr(scores, "tolist"):
            return [float(x) for x in scores.tolist()]
        return [float(x) for x in list(scores)]

    mode = (settings.reranker_backend or "auto").strip().lower()
    if mode == "cross_encoder":
        model = _cross_encoder()
        scores = _scores_to_list(model.predict([(a, b) for a, b in pairs]))
    elif mode == "flag":
        model = _flag_reranker()
        scores = _scores_to_list(model.compute_score(pairs))
    else:
        try:
            model = _flag_reranker()
            scores = _scores_to_list(model.compute_score(pairs))
        except Exception:
            model = _cross_encoder()
            scores = _scores_to_list(model.predict([(a, b) for a, b in pairs]))
    ranked = sorted(zip(items, scores), key=lambda x: float(x[1]), reverse=True)
    out: list[dict[str, Any]] = []
    for doc, s in ranked[:k]:
        row = dict(doc)
        row["rerank_score"] = float(s)
        out.append(row)
    return out
