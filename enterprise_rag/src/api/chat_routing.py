"""Chat latency tiers and routing-related memory overrides."""

from __future__ import annotations

from typing import Any


def apply_routing_tier(mem: dict[str, Any]) -> dict[str, Any]:
    """
    fast:     rules-only condense, no kb LLM judge (min LLM calls)
    balanced: default heuristics + edge LLM judge
    quality:  always LLM-verify KB when retrieval hits
    """
    out = dict(mem)
    tier = str(out.get("chat_routing_tier") or "balanced").strip().lower()
    if tier == "fast":
        out["condense_llm_enabled"] = False
        out["kb_llm_judge"] = False
        out["kb_llm_judge_always"] = False
    elif tier == "quality":
        out["condense_llm_enabled"] = True
        out["kb_llm_judge"] = True
        out["kb_llm_judge_always"] = True
    else:
        out.setdefault("condense_llm_enabled", True)
        out.setdefault("kb_llm_judge_always", False)
    out["chat_routing_tier"] = tier if tier in ("fast", "balanced", "quality") else "balanced"
    return out
