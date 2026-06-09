"""Execute processing tool chain for ingest."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from document_loader.processing.modes import UNCLEANED, normalize_ingest_mode
from document_loader.processing.registry import load_config
from document_loader.processing.router import select_tools
from document_loader.processing.tools import run_tool


@dataclass
class ProcessResult:
    text: str
    tools_used: list[str] = field(default_factory=list)
    router: str = "rule"
    file_type: str = ""


def process_upload_file(
    path: Path,
    *,
    mode: str = UNCLEANED,
    llm_runtime: dict[str, Any] | None = None,
) -> ProcessResult:
    """
    mode:
      - pre_cleaned: 已清洗数据，仅 extract + 空白规范化
      - uncleaned: 未清洗数据，完整工具链 + 可选 LLM 路由
    """
    norm = normalize_ingest_mode(mode)
    cfg = load_config()
    use_llm = bool(cfg.get("use_llm_router", True)) and norm == UNCLEANED
    chain, router = select_tools(
        path,
        mode=norm,
        use_llm=use_llm,
        llm_runtime=llm_runtime,
        cfg=cfg,
    )
    if not chain:
        raise RuntimeError(f"无可用处理工具，扩展名 {path.suffix}")

    text = ""
    resolved = str(path.resolve())
    for tid in chain:
        if tid.startswith("extract_"):
            text = run_tool(tid, path=resolved)
        else:
            text = run_tool(tid, text=text or "")

    text = (text or "").strip()
    if not text:
        raise RuntimeError(f"未能从文件中提取有效文本：{path.name}")

    return ProcessResult(
        text=text,
        tools_used=chain,
        router=router,
        file_type=path.suffix.lower().lstrip("."),
    )
