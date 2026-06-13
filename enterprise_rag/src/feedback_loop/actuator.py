"""Execute approved feedback actions (Sprint C whitelist)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.prompt_config_store import load_prompt_slots, save_prompt_config
from api.ui_config_store import DEFAULT_UI_CONFIG, load_ui_config, save_ui_config
from config import settings
from feedback_loop.config_revisions import append_revision
from retrieval.retrieval_tuning_store import load_retrieval_tuning, save_retrieval_tuning

BLOCKED_ACTIONS = frozenset({"delete_index"})

UI_CONFIG_PATCH_FIELDS = frozenset(
    {
        "kb_min_score",
        "kb_min_rerank_score",
        "stream_verifier_enabled",
        "graph_verifier_enabled",
        "hybrid_expert_mode",
    }
)

RETRIEVAL_TUNING_FIELDS = frozenset({"hybrid_vector_weight", "hybrid_bm25_weight"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _golden_path() -> Path:
    return Path(settings.golden_jsonl_path)


def _proposals_path() -> Path:
    return Path(settings.ingest_proposals_path)


def _extract_context_texts(row: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    snap = row.get("trace_snapshot")
    if not isinstance(snap, dict):
        return texts
    for sp in snap.get("spans") or []:
        if not isinstance(sp, dict):
            continue
        output = sp.get("output") or {}
        if isinstance(output, dict) and "result" in output:
            inner = output.get("result")
            if isinstance(inner, dict):
                output = inner
        if not isinstance(output, dict):
            continue
        for meta in output.get("contexts_meta") or []:
            if not isinstance(meta, dict):
                continue
            text = str(meta.get("text") or "").strip()
            if text:
                texts.append(text[:2000])
        for ctx in output.get("contexts") or []:
            piece = str(ctx or "").strip()
            if piece:
                texts.append(piece[:2000])
    return texts[:8]


def _build_golden_record(row: dict[str, Any]) -> dict[str, Any]:
    question = str(row.get("question") or "").strip()
    answer = str(row.get("answer_preview") or "").strip()
    correction = str(row.get("correction") or "").strip()
    contexts = _extract_context_texts(row)
    if not contexts and answer:
        contexts = [answer[:500]]
    ground_truth = correction or answer
    return {
        "question": question or "（无问题文本）",
        "answer": answer,
        "contexts": contexts,
        "ground_truth": ground_truth,
        "meta": {
            "feedback_id": row.get("id"),
            "rating": row.get("rating"),
            "issue_type": row.get("issue_type"),
            "sources": row.get("sources") or [],
        },
    }


def _should_run_add_to_golden(
    row: dict[str, Any],
    action: dict[str, Any],
    *,
    manual: bool,
) -> bool:
    if manual:
        return True
    if not settings.feedback_auto_add_to_golden:
        return False
    try:
        conf = float(action.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    return (
        conf >= float(settings.feedback_auto_add_to_golden_min_confidence)
        and _row_rating(row) <= 0
    )


def _row_rating(row: dict[str, Any]) -> int:
    try:
        return int(row.get("rating") or 0)
    except (TypeError, ValueError):
        return 0


def action_add_to_golden(row: dict[str, Any], action: dict[str, Any], *, manual: bool) -> dict[str, Any]:
    if not _should_run_add_to_golden(row, action, manual=manual):
        return {
            "action": "add_to_golden",
            "ok": False,
            "skipped": True,
            "reason": "confidence below threshold or auto disabled",
        }
    record = _build_golden_record(row)
    path = _golden_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"action": "add_to_golden", "ok": True, "golden_path": str(path)}


def action_propose_reingest(row: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    proposal = {
        "id": uuid.uuid4().hex,
        "created_at": _utc_now(),
        "feedback_id": row.get("id"),
        "tenant_id": row.get("tenant_id") or "internal",
        "sources": list(row.get("sources") or []),
        "question": row.get("question"),
        "issue_type": row.get("issue_type"),
        "detail": str(action.get("detail") or ""),
        "status": "pending_human_confirm",
    }
    path = _proposals_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(proposal, ensure_ascii=False) + "\n")
    return {"action": "propose_reingest", "ok": True, "proposal_id": proposal["id"]}


def _default_config_patch(row: dict[str, Any]) -> dict[str, Any]:
    issue = str(row.get("issue_type") or "")
    if issue == "retrieval_miss":
        ui = load_ui_config()
        cur = float(ui.get("kb_min_score") or 0.55)
        return {"ui_config": {"kb_min_score": max(0.3, round(cur - 0.05, 3))}}
    return {}


def _snapshot_config_state() -> dict[str, Any]:
    return {
        "ui_config": load_ui_config(),
        "retrieval_tuning": load_retrieval_tuning(),
        "prompt_slots": load_prompt_slots(),
    }


def restore_config_snapshot(snapshot: dict[str, Any]) -> None:
    ui = snapshot.get("ui_config")
    if isinstance(ui, dict):
        allowed = {k: ui[k] for k in UI_CONFIG_PATCH_FIELDS if k in ui}
        if allowed:
            save_ui_config(allowed)
    tuning = snapshot.get("retrieval_tuning")
    if isinstance(tuning, dict):
        save_retrieval_tuning(tuning)
    slots = snapshot.get("prompt_slots")
    if isinstance(slots, list) and slots:
        save_prompt_config(slots=slots)
    _invalidate_search_cache()


def _apply_prompt_slot_patch(slot_patch: dict[str, Any]) -> bool:
    sid = str(slot_patch.get("id") or "").strip().lower()
    content = slot_patch.get("content")
    if not sid or content is None:
        return False
    slots = load_prompt_slots()
    updated = False
    for slot in slots:
        if str(slot.get("id") or "") == sid:
            slot["content"] = str(content).strip()[:8000]
            updated = True
            break
    if not updated:
        return False
    save_prompt_config(slots=slots)
    return True


def action_apply_config_patch(
    row: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    raw_patch = action.get("patch")
    if not isinstance(raw_patch, dict) or not raw_patch:
        raw_patch = _default_config_patch(row)
    if not raw_patch:
        return {
            "action": "apply_config_patch",
            "ok": False,
            "skipped": True,
            "reason": "no patch provided",
        }

    before = _snapshot_config_state()
    applied: dict[str, Any] = {}

    ui_patch = raw_patch.get("ui_config")
    if isinstance(ui_patch, dict) and ui_patch:
        filtered = {
            k: v
            for k, v in ui_patch.items()
            if k in UI_CONFIG_PATCH_FIELDS and k in DEFAULT_UI_CONFIG
        }
        if filtered:
            save_ui_config(filtered)
            applied["ui_config"] = filtered

    tuning_patch = raw_patch.get("retrieval_tuning")
    if isinstance(tuning_patch, dict) and tuning_patch:
        filtered = {k: v for k, v in tuning_patch.items() if k in RETRIEVAL_TUNING_FIELDS}
        if filtered:
            save_retrieval_tuning(filtered)
            applied["retrieval_tuning"] = filtered

    slot_patch = raw_patch.get("prompt_slot")
    if isinstance(slot_patch, dict) and slot_patch:
        if _apply_prompt_slot_patch(slot_patch):
            applied["prompt_slot"] = {
                "id": slot_patch.get("id"),
                "content": str(slot_patch.get("content") or "")[:200],
            }

    if not applied:
        return {
            "action": "apply_config_patch",
            "ok": False,
            "skipped": True,
            "reason": "patch fields not in whitelist",
        }

    after = _snapshot_config_state()
    revision = append_revision(
        feedback_id=str(row.get("id") or ""),
        action="apply_config_patch",
        before=before,
        after=after,
        patch=applied,
        tenant_id=str(row.get("tenant_id") or "internal"),
    )
    _invalidate_search_cache()
    return {
        "action": "apply_config_patch",
        "ok": True,
        "revision_id": revision["id"],
        "applied": applied,
    }


def _invalidate_search_cache() -> None:
    try:
        from retrieval.search_cache import invalidate_search_cache

        invalidate_search_cache()
    except Exception:
        pass


def execute_single_action(
    row: dict[str, Any],
    action: dict[str, Any],
    *,
    manual: bool = True,
) -> dict[str, Any]:
    name = str(action.get("action") or "").strip()
    if not name:
        return {"action": "", "ok": False, "error": "missing action"}
    if name in BLOCKED_ACTIONS:
        return {"action": name, "ok": False, "error": "blocked action"}

    if name == "add_to_golden":
        return action_add_to_golden(row, action, manual=manual)
    if name == "propose_reingest":
        return action_propose_reingest(row, action)
    if name == "apply_config_patch":
        return action_apply_config_patch(row, action)
    return {"action": name, "ok": False, "error": "unknown action"}


def execute_feedback_actions(row: dict[str, Any], *, manual: bool = True) -> list[dict[str, Any]]:
    actions = row.get("suggested_actions") or []
    results: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        results.append(execute_single_action(row, action, manual=manual))
    return results
