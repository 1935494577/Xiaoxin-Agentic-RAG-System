"""Route questions to Classic / Graph / Agentic RAG architectures."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from agent.input_modes import DocTaskType, InputMode
from config import settings

RagArchitecture = Literal["classic", "graph", "agentic"]
RagArchitectureOverride = Literal["auto", "classic", "graph", "agentic"]

_CLASSIC_RE = re.compile(
    r"多久|多少|截止日期|什么时候|如何配置|怎么配置|适用范围|是什么|什么是|"
    r"有哪些要求|步骤|流程是什么|规定是什么",
    re.IGNORECASE,
)
_GRAPH_RE = re.compile(
    r"依赖|影响|关联|审批链|上下游|和谁有关|与哪些|哪些.*依赖|哪些.*影响|"
    r"涉及哪些|关系链|谁负责|谁审批|下游|上游|关联的|有关",
    re.IGNORECASE,
)
_AGENTIC_RE = re.compile(
    r"分析.*原因|排查|调查|综合研究|对比竞品|可能来自哪个环节|来自哪个环节|哪个环节|"
    r"为什么.*下降|为什么.*异常|背景是什么|全面评估|多维度|业务异常|"
    r"关系图|组织图|汇报关系|人物关系|架构图|上下级|谁是谁的|"
    r"公司关系|人员关系|员工关系|组织架构|展示.{0,8}关系|深层公司",
    re.IGNORECASE,
)

_POLICY_CACHE: dict[str, Any] | None = None


def _policy_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "config" / "rag_architecture_policy.json"


def load_rag_architecture_policy() -> dict[str, Any]:
    global _POLICY_CACHE
    if _POLICY_CACHE is not None:
        return _POLICY_CACHE
    path = _policy_path()
    default: dict[str, Any] = {"departments": {}, "scenarios": {}, "force_classic_patterns": []}
    if not path.is_file():
        _POLICY_CACHE = default
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            _POLICY_CACHE = default
            return default
        _POLICY_CACHE = data
        return data
    except Exception:
        _POLICY_CACHE = default
        return default


def invalidate_policy_cache() -> None:
    global _POLICY_CACHE
    _POLICY_CACHE = None


def _rule_signals(question: str) -> tuple[int, int, int]:
    q = (question or "").strip()
    classic = 1 if _CLASSIC_RE.search(q) and not _GRAPH_RE.search(q) and not _AGENTIC_RE.search(q) else 0
    graph = 1 if _GRAPH_RE.search(q) else 0
    agentic = 1 if _AGENTIC_RE.search(q) else 0
    return classic, graph, agentic


def _apply_department_policy(
    arch: RagArchitecture,
    department: str,
    policy: dict[str, Any],
) -> tuple[RagArchitecture, bool]:
    dept_cfg = (policy.get("departments") or {}).get(department.strip()) or {}
    allowed = dept_cfg.get("allowed") or ["classic", "graph", "agentic"]
    allowed_set = {str(a).lower() for a in allowed}
    if arch in allowed_set:
        return arch, False
    if "classic" in allowed_set:
        return "classic", True
    return "classic", True


def _scenario_prefer(
    scenario_tags: list[str] | None,
    policy: dict[str, Any],
) -> RagArchitecture | None:
    scenarios = policy.get("scenarios") or {}
    for tag in scenario_tags or []:
        row = scenarios.get(str(tag).strip())
        if isinstance(row, dict):
            prefer = str(row.get("prefer") or "").strip().lower()
            if prefer in ("classic", "graph", "agentic"):
                return prefer  # type: ignore[return-value]
    return None


def _llm_classify_architecture(
    question: str,
    llm_runtime: dict[str, Any],
) -> RagArchitecture | None:
    api_key = (llm_runtime.get("llm_api_key") or "").strip() or settings.openai_api_key
    if not api_key:
        return None
    try:
        from openai import OpenAI

        from agent.llm_routing import model_for_task

        api_base = (llm_runtime.get("llm_api_base") or "").strip() or settings.openai_api_base
        headers = llm_runtime.get("llm_extra_headers")
        client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
        if isinstance(headers, dict) and headers:
            client_kw["default_headers"] = headers
        client = OpenAI(**client_kw)
        model = model_for_task(llm_runtime, task="routing")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是 RAG 架构分类器。仅输出一个词：CLASSIC、GRAPH 或 AGENTIC。\n"
                        "CLASSIC=单段资料可答的事实/配置/政策题；"
                        "GRAPH=跨实体关系/依赖/审批链/关联对象；"
                        "AGENTIC=需多步调查分析原因/排查/综合研究。"
                    ),
                },
                {"role": "user", "content": question[:1500]},
            ],
            temperature=0.0,
            max_tokens=8,
        )
        tag = (resp.choices[0].message.content or "").strip().upper()
        if tag.startswith("GRAPH"):
            return "graph"
        if tag.startswith("AGENTIC"):
            return "agentic"
        if tag.startswith("CLASSIC"):
            return "classic"
    except Exception:
        return None
    return None


def resolve_rag_architecture(
    question: str,
    *,
    department: str = "",
    input_mode: InputMode = "question",
    doc_task_type: DocTaskType | None = None,
    scenario_tags: list[str] | None = None,
    policy: dict[str, Any] | None = None,
    request_override: RagArchitectureOverride | str | None = "auto",
    router_enabled: bool = True,
    llm_fallback: bool = False,
    llm_runtime: dict[str, Any] | None = None,
) -> tuple[RagArchitecture, dict[str, Any]]:
    """
    Resolve RAG architecture. Fail-closed to classic when uncertain.
    Returns (architecture, meta) for trace/SSE.
    """
    meta: dict[str, Any] = {"layer": "rules"}
    pol = policy if policy is not None else load_rag_architecture_policy()

    override = (request_override or "auto").strip().lower()
    if override in ("classic", "graph", "agentic"):
        arch: RagArchitecture = override  # type: ignore[assignment]
        meta["layer"] = "manual_override"
        arch, clamped = _apply_department_policy(arch, department, pol)
        if clamped:
            meta["department_clamped"] = True
        return arch, meta

    if not router_enabled:
        meta["router_disabled"] = True
        return "classic", meta

    if input_mode == "temp_document":
        meta["input_mode_hint"] = "temp_document"
        return "classic", meta

    if input_mode == "doc_task":
        meta["input_mode_hint"] = "doc_task"
        if doc_task_type in ("compare",):
            meta["doc_task_hint"] = doc_task_type
            arch = "agentic"
            arch, clamped = _apply_department_policy(arch, department, pol)
            if clamped:
                meta["department_clamped"] = True
            return arch, meta
        if doc_task_type in ("summary", "extract", "annotate"):
            meta["doc_task_hint"] = doc_task_type
            return "classic", meta

    prefer = _scenario_prefer(scenario_tags, pol)
    if prefer:
        meta["scenario_prefer"] = prefer
        arch, clamped = _apply_department_policy(prefer, department, pol)
        if clamped:
            meta["department_clamped"] = True
        return arch, meta

    classic_s, graph_s, agentic_s = _rule_signals(question)
    if agentic_s and not graph_s:
        meta["layer"] = "rules"
        meta["signal"] = "agentic"
        arch = "agentic"
        arch, clamped = _apply_department_policy(arch, department, pol)
        if clamped:
            meta["department_clamped"] = True
        return arch, meta
    if graph_s and not agentic_s:
        meta["layer"] = "rules"
        meta["signal"] = "graph"
        arch = "graph"
        arch, clamped = _apply_department_policy(arch, department, pol)
        if clamped:
            meta["department_clamped"] = True
        return arch, meta
    if classic_s and not graph_s and not agentic_s:
        meta["layer"] = "rules"
        meta["signal"] = "classic"
        return "classic", meta

    if graph_s and agentic_s:
        meta["layer"] = "rules"
        meta["signal"] = "graph+agentic"
        arch = "agentic"
        arch, clamped = _apply_department_policy(arch, department, pol)
        if clamped:
            meta["department_clamped"] = True
        return arch, meta

    if llm_fallback and llm_runtime:
        llm_arch = _llm_classify_architecture(question, llm_runtime)
        if llm_arch:
            meta["layer"] = "llm"
            arch, clamped = _apply_department_policy(llm_arch, department, pol)
            if clamped:
                meta["department_clamped"] = True
            return arch, meta

    meta["layer"] = "default"
    return "classic", meta
