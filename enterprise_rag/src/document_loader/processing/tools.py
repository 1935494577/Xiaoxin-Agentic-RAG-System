"""LangChain-compatible document processing tools (extract + clean)."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from document_loader.cleaner import clean_text, redact_pii, scrub_basic, strip_watermark_lines
from document_loader.parser import load_document_text


class PathInput(BaseModel):
    path: str = Field(description="Absolute or relative path to the document file")


class TextInput(BaseModel):
    text: str = Field(description="Document text to process")


def _extract_plain(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="ignore")


def _extract_pdf(path: str) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix not in {".pdf"}:
        return load_document_text(p)
    try:
        import pdfplumber

        parts: list[str] = []
        with pdfplumber.open(p) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        if text:
            return text
    except Exception:
        pass
    return load_document_text(p)


def _extract_office_html(path: str) -> str:
    return load_document_text(Path(path))


def _scrub(text: str) -> str:
    return scrub_basic(text)


def _watermark(text: str) -> str:
    return strip_watermark_lines(text)


def _pii(text: str) -> str:
    return redact_pii(text)


def _full_clean(text: str) -> str:
    return clean_text(text, use_presidio=True)


TOOL_DEFINITIONS: dict[str, dict] = {
    "extract_plain": {
        "description": "Extract text from .txt / .md / .markdown plain text files.",
        "func": _extract_plain,
        "args_schema": PathInput,
        "input": "path",
        "types": [".txt", ".md", ".markdown"],
    },
    "extract_pdf": {
        "description": "Extract text from PDF files using pdfplumber with unstructured fallback.",
        "func": _extract_pdf,
        "args_schema": PathInput,
        "input": "path",
        "types": [".pdf"],
    },
    "extract_office_html": {
        "description": "Extract text from DOCX, HTML, and other office/web formats via unstructured.",
        "func": _extract_office_html,
        "args_schema": PathInput,
        "input": "path",
        "types": [".docx", ".html", ".htm"],
    },
    "scrub_whitespace": {
        "description": "Normalize whitespace and remove zero-width characters from extracted text.",
        "func": _scrub,
        "args_schema": TextInput,
        "input": "text",
    },
    "strip_watermarks": {
        "description": "Remove confidential watermark lines from document text.",
        "func": _watermark,
        "args_schema": TextInput,
        "input": "text",
    },
    "redact_pii": {
        "description": "Redact emails, phone numbers and sensitive entities (Presidio with regex fallback).",
        "func": _pii,
        "args_schema": TextInput,
        "input": "text",
    },
}


def build_langchain_tools(enabled: set[str] | None = None) -> list[StructuredTool]:
    out: list[StructuredTool] = []
    for tid, meta in TOOL_DEFINITIONS.items():
        if enabled is not None and tid not in enabled:
            continue
        out.append(
            StructuredTool.from_function(
                func=meta["func"],
                name=tid,
                description=str(meta["description"]),
                args_schema=meta["args_schema"],
            )
        )
    return out


def run_tool(tool_id: str, **kwargs) -> str:
    meta = TOOL_DEFINITIONS.get(tool_id)
    if not meta:
        raise ValueError(f"Unknown tool: {tool_id}")
    fn = meta["func"]
    if meta["input"] == "path":
        return str(fn(kwargs["path"]))
    return str(fn(kwargs["text"]))
