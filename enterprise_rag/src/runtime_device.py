"""Torch device resolution for laptop RTX 3060 (6GB) / CPU fallback."""

from __future__ import annotations

from functools import lru_cache

from config import settings


def cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


@lru_cache
def torch_device_string() -> str:
    """Returns 'cuda' or 'cpu' based on settings.torch_device and hardware."""
    mode = (settings.torch_device or "auto").lower()
    if mode == "cpu":
        return "cpu"
    if mode == "cuda":
        return "cuda" if cuda_available() else "cpu"
    # auto
    return "cuda" if cuda_available() else "cpu"


def use_fp16_safe() -> bool:
    return bool(settings.use_fp16) and torch_device_string() == "cuda"
