import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

from document_loader.parser import load_document_text
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

_ANALYZER = None
_ANONYMIZER: AnonymizerEngine | None = None
_PRESIDIO_DISABLED = False
_PRESIDIO_INIT_TIMEOUT_SEC = 8.0


def _init_analyzer():
    from presidio_analyzer import AnalyzerEngine

    return AnalyzerEngine()


def _engines():
    global _ANALYZER, _ANONYMIZER, _PRESIDIO_DISABLED
    if _PRESIDIO_DISABLED:
        raise RuntimeError("presidio unavailable")
    if _ANALYZER is None:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_init_analyzer)
            try:
                _ANALYZER = fut.result(timeout=_PRESIDIO_INIT_TIMEOUT_SEC)
            except FuturesTimeoutError as e:
                _PRESIDIO_DISABLED = True
                raise RuntimeError("presidio init timed out") from e
    if _ANONYMIZER is None:
        _ANONYMIZER = AnonymizerEngine()
    return _ANALYZER, _ANONYMIZER


def redact_pii(text: str, language: str = "zh") -> str:
    """使用 Presidio 做实体级脱敏；失败时回退为简单邮箱/电话掩码。"""
    try:
        analyzer, anonymizer = _engines()
        results = analyzer.analyze(text=text, language=language)
        operators = {"DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"})}
        return anonymizer.anonymize(text=text, analyzer_results=results, operators=operators).text
    except Exception:
        text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<email>", text)
        text = re.sub(r"\+?\d[\d\s\-]{7,}\d", "<phone>", text)
        return text


def strip_watermark_lines(text: str, keywords: tuple[str, ...] = ("机密", "内部资料", "CONFIDENTIAL")) -> str:
    lines = []
    for line in text.splitlines():
        if any(k in line for k in keywords) and len(line) < 80:
            continue
        lines.append(line)
    return "\n".join(lines)


def clean_text(text: str, use_presidio: bool = True) -> str:
    text = strip_watermark_lines(text)
    if use_presidio:
        text = redact_pii(text)
    return text


def clean_raw_text(text: str, use_presidio: bool = True) -> str:
    """对纯文本做 scrub + 与文件入库相同的清洗逻辑（供预览 / 文本入库）。"""
    text = scrub_basic(text)
    return clean_text(text, use_presidio=use_presidio)


def scrub_basic(text: str) -> str:
    """轻量清洗：折叠空白、去除零宽字符。"""
    for z in ("\u200b", "\u200c", "\u200d", "\ufeff"):
        text = text.replace(z, "")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def clean_file(path: Path, use_presidio: bool = True) -> str:
    raw = load_document_text(path)
    text = scrub_basic(raw)
    return clean_text(text, use_presidio=use_presidio)
