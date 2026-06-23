"""Branding / UI settings persisted on disk (shared by API and Streamlit)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings

DEFAULT_UI_CONFIG: dict[str, Any] = {
    "logo_en": "JNAO",
    "logo_cn": "劲脑",
    "logo_image_path": "",
    "app_title": "入库小帮手",
    "app_tagline": "把文档放进知识库，用自然语言提问；无需编写代码。",
    "suggested_questions": [
        "1-3年级超脑阅读要求是什么？",
        "这些文档属于哪个部门？",
        "扫描速记有哪些注意事项？",
    ],
    "stream_fast_mode": True,
    "max_history_turns": 6,
    "max_history_chars": 6000,
    "kb_min_score": 0.55,
    "kb_min_rerank_score": 0.12,
    "kb_llm_judge": True,
    "citation_max_sources": 2,
    "citation_min_relative_score": 0.75,
    "general_fallback_enabled": False,
    "kb_post_stream_fallback": False,
    "hybrid_expert_mode": False,
    "stream_verifier_enabled": False,
    "graph_verifier_enabled": False,
    "long_term_memory_enabled": True,
    "conversation_condense_enabled": True,
    "history_prune_enabled": True,
    "history_prune_min_similarity": 0.35,
    "history_prune_max_turns": 4,
    "history_assistant_max_chars": 600,
    "rolling_summary_enabled": True,
    "rolling_summary_every_n_turns": 6,
    "rolling_summary_min_chars": 3500,
    "rolling_summary_max_tokens": 400,
    "routing_model": "",
    "chat_routing_tier": "balanced",
    "condense_llm_enabled": True,
    "kb_llm_judge_always": False,
    "agent_reasoning_mode": "direct",
    "scene_preset": "kb_frontline",
    "ingest_tag_presets": ["制度", "培训", "产品", "FAQ", "内部"],
    "rag_arch_router_enabled": True,
    "rag_arch_llm_fallback": False,
    "default_rag_architecture": "auto",
    "graph_extraction_enabled": True,
    "agentic_max_turns": 6,
    "agentic_max_kb_searches": 4,
    "clarify_enabled": False,
}

SUPPORTED_UPLOAD_EXTENSIONS = ("txt", "md", "pdf", "docx", "html")
SUPPORTED_UPLOAD_LABEL = "TXT · MD · PDF · DOCX · HTML"


def _config_path() -> Path:
    return Path(settings.ui_config_path)


def _branding_dir() -> Path:
    d = Path(settings.ui_branding_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_ui_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return dict(DEFAULT_UI_CONFIG)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(DEFAULT_UI_CONFIG)
        merged = dict(DEFAULT_UI_CONFIG)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_UI_CONFIG)


def save_ui_config(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_ui_config()
    allowed = set(DEFAULT_UI_CONFIG.keys())
    for k, v in patch.items():
        if k not in allowed:
            continue
        if k == "suggested_questions" and isinstance(v, list):
            current[k] = [str(x).strip() for x in v if str(x).strip()][:12]
        elif k == "ingest_tag_presets" and isinstance(v, list):
            current[k] = [str(x).strip() for x in v if str(x).strip()][:30]
        elif v is not None:
            current[k] = v
    _config_path().parent.mkdir(parents=True, exist_ok=True)
    _config_path().write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def resolve_effective_reasoning_mode(
    ui: dict[str, Any] | None = None,
    *,
    hybrid_expert: bool | None = None,
) -> str:
    """KB-only paths use direct (faster); hybrid/general paths keep configured react/plan."""
    from agent.reasoning_modes import normalize_reasoning_mode

    cfg = ui or load_ui_config()
    configured = normalize_reasoning_mode(str(cfg.get("agent_reasoning_mode") or "direct"))
    hybrid = bool(cfg.get("hybrid_expert_mode")) if hybrid_expert is None else bool(hybrid_expert)
    if not hybrid and configured == "react":
        return "direct"
    return configured


def public_ui_config() -> dict[str, Any]:
    from agent.persona_presets import PERSONA_PRESETS
    from agent.reasoning_modes import REASONING_MODES, normalize_reasoning_mode
    from api.prompt_config_store import load_active_persona_id
    from api.scene_presets import list_scene_presets_public

    cfg = load_ui_config()
    logo_path = str(cfg.get("logo_image_path") or "").strip()
    has_logo_image = bool(logo_path and Path(logo_path).is_file())
    persona_id = load_active_persona_id()
    persona_meta = PERSONA_PRESETS.get(persona_id, {})
    reasoning_mode = resolve_effective_reasoning_mode(cfg)
    reasoning_meta = REASONING_MODES.get(reasoning_mode, {})
    return {
        **cfg,
        "has_logo_image": has_logo_image,
        "supported_upload_extensions": list(SUPPORTED_UPLOAD_EXTENSIONS),
        "supported_upload_label": SUPPORTED_UPLOAD_LABEL,
        "active_persona_id": persona_id,
        "active_persona_label": str(persona_meta.get("label") or persona_id),
        "agent_reasoning_mode": reasoning_mode,
        "agent_reasoning_mode_label": str(reasoning_meta.get("label") or reasoning_mode),
        "scene_presets": list_scene_presets_public(),
    }


def save_logo_file(filename: str, content: bytes) -> str:
    ext = Path(filename or "logo.png").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}:
        ext = ".png"
    dest = _branding_dir() / f"logo{ext}"
    for old in _branding_dir().glob("logo.*"):
        if old != dest:
            old.unlink(missing_ok=True)
    dest.write_bytes(content)
    cfg = save_ui_config({"logo_image_path": str(dest)})
    return str(cfg.get("logo_image_path") or dest)


def resolve_logo_file() -> Path | None:
    p = Path(str(load_ui_config().get("logo_image_path") or ""))
    return p if p.is_file() else None
