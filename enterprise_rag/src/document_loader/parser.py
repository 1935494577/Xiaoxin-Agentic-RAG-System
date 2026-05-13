from pathlib import Path


def load_document_text(path: Path) -> str:
    """步骤1：解析入口；若配置 LLAMA_CLOUD_API_KEY 则优先 LlamaParse，否则 unstructured/pdfplumber。"""
    from config import settings as s
    if s.llama_cloud_api_key:
        try:
            from llama_parse import LlamaParse

            parser = LlamaParse(api_key=s.llama_cloud_api_key, result_type="markdown")
            documents = parser.load_data(str(path))
            return "".join((getattr(d, "text", "") or "") + "\n" for d in documents)
        except Exception:
            pass

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            import pdfplumber

            parts: list[str] = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except Exception:
            pass
        try:
            from unstructured.partition.auto import partition

            elements = partition(filename=str(path))
            return "\n\n".join(str(el) for el in elements)
        except Exception as e:
            raise RuntimeError(f"无法解析 PDF: {path}") from e

    try:
        from unstructured.partition.auto import partition

        elements = partition(filename=str(path))
        return "\n\n".join(str(el) for el in elements)
    except Exception as e:
        raise RuntimeError(f"不支持的文件类型或解析失败: {path} ({e})") from e
