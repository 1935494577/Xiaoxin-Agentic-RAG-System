"""Select processing tools by file type — rule router + optional LLM tool-calling."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from document_loader.processing.modes import UNCLEANED, normalize_ingest_mode
from document_loader.processing.registry import enabled_tool_ids, load_config
from document_loader.processing.tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

PRE_CLEANED_POST_TOOLS = ("scrub_whitespace",)
UNCLEANED_POST_TOOLS = ("scrub_whitespace", "strip_watermarks", "redact_pii")


def rule_select_tools(path: Path, *, mode: str, cfg: dict[str, Any] | None = None) -> list[str]:
    """Deterministic tool chain from extension + ingest mode."""
    c = cfg or load_config()
    enabled = enabled_tool_ids(c)
    ext = path.suffix.lower()
    ext_map = c.get("extension_map") or {}
    extract_id = ext_map.get(ext)
    if not extract_id:
        for tid, meta in TOOL_DEFINITIONS.items():
            if ext in (meta.get("types") or []):
                extract_id = tid
                break
    if not extract_id:
        extract_id = "extract_office_html"
    chain: list[str] = []
    if extract_id in enabled:
        chain.append(extract_id)
    norm = normalize_ingest_mode(mode)
    post = UNCLEANED_POST_TOOLS if norm == UNCLEANED else PRE_CLEANED_POST_TOOLS
    for tid in post:
        if tid in enabled:
            chain.append(tid)
    return chain


def llm_select_tools(
    path: Path,
    *,
    mode: str,
    llm_runtime: dict[str, Any],
    cfg: dict[str, Any] | None = None,
) -> list[str] | None:
    """Ask OpenAI-compatible model to pick tools via bind_tools; returns None on failure."""
    c = cfg or load_config()
    enabled = enabled_tool_ids(c)
    if not enabled:
        return None

    api_key = (llm_runtime.get("llm_api_key") or "").strip()
    if not api_key:
        return None

    try:
        from langchain_core.messages import HumanMessage, ToolMessage
        from langchain_openai import ChatOpenAI

        from document_loader.processing.tools import build_langchain_tools

        tools = build_langchain_tools(enabled)
        if not tools:
            return None

        client_kw: dict[str, Any] = {
            "model": llm_runtime.get("chat_model") or "gpt-4o-mini",
            "api_key": api_key,
            "base_url": llm_runtime.get("llm_api_base"),
            "temperature": 0,
        }
        headers = llm_runtime.get("llm_extra_headers")
        if isinstance(headers, dict) and headers:
            client_kw["default_headers"] = headers

        llm = ChatOpenAI(**client_kw)
        bound = llm.bind_tools(tools)

        ext = path.suffix.lower()
        norm = normalize_ingest_mode(mode)
        mode_hint = (
            "未清洗模式：需提取并做空白规范化、水印过滤、脱敏。"
            if norm == UNCLEANED
            else "已清洗模式：数据已预处理，仅提取并做空白规范化后入库。"
        )
        prompt = (
            f"入库文件：{path.name}，扩展名 {ext}。\n"
            f"{mode_hint}\n"
            "请调用合适的工具完成处理。先调用一个 extract_* 工具读取文件，再按需调用文本清洗工具。"
            f"文件路径参数：{str(path.resolve())}"
        )
        messages: list[Any] = [HumanMessage(content=prompt)]
        response = bound.invoke(messages)
        selected: list[str] = []
        if getattr(response, "tool_calls", None):
            for call in response.tool_calls:
                name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
                if name and name in enabled:
                    selected.append(str(name))
        if selected:
            return selected
    except Exception as e:
        logger.warning("LLM ingest router failed: %s", e)
    return None


def select_tools(
    path: Path,
    *,
    mode: str,
    use_llm: bool,
    llm_runtime: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
) -> tuple[list[str], str]:
    """Return (tool_chain, router_kind)."""
    if use_llm and llm_runtime:
        llm_chain = llm_select_tools(path, mode=mode, llm_runtime=llm_runtime, cfg=cfg)
        if llm_chain:
            return llm_chain, "llm"
    return rule_select_tools(path, mode=mode, cfg=cfg), "rule"
