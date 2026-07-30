"""Extract DOCX exam text with MathType/OLE/drawing placeholders so formulas are not dropped."""

from __future__ import annotations

import re
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
V_NS = "urn:schemas-microsoft-com:vml"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

W = "{%s}" % W_NS
R = "{%s}" % R_NS
A = "{%s}" % A_NS
V = "{%s}" % V_NS


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _load_rel_map(zf: zipfile.ZipFile) -> dict[str, str]:
    """rId -> word/media/... path."""
    out: dict[str, str] = {}
    try:
        rels_xml = zf.read("word/_rels/document.xml.rels")
    except KeyError:
        return out
    root = ET.fromstring(rels_xml)
    for rel in root:
        if _local(rel.tag) != "Relationship":
            continue
        rid = rel.attrib.get("Id") or ""
        target = rel.attrib.get("Target") or ""
        if not rid or not target:
            continue
        if target.startswith("/"):
            path = target.lstrip("/")
        else:
            path = "word/" + target.lstrip("/")
        # normalize
        path = path.replace("\\", "/")
        while "/../" in path:
            path = re.sub(r"[^/]+/\.\./", "", path)
        out[rid] = path
    return out


def _collect_media_rids(el: ET.Element) -> list[str]:
    """Find relationship ids for images/OLE under an element."""
    rids: list[str] = []
    for node in el.iter():
        tag = _local(node.tag)
        # a:blip r:embed
        if tag == "blip":
            rid = node.attrib.get(f"{{{R_NS}}}embed") or node.attrib.get("embed")
            if rid:
                rids.append(rid)
        # v:imagedata r:id
        if tag == "imagedata":
            rid = (
                node.attrib.get(f"{{{R_NS}}}id")
                or node.attrib.get("r:id")
                or node.attrib.get("id")
            )
            if rid:
                rids.append(rid)
        # o:OLEObject
        if tag == "OLEObject":
            rid = node.attrib.get(f"{{{R_NS}}}id") or node.attrib.get("r:id")
            if rid:
                rids.append(rid)
    return rids


_DISPLAY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".wmf", ".emf", ".tif", ".tiff", ".bmp"}


def _media_rid_score(rid: str, rel_map: dict[str, str]) -> int:
    """Lower is better: raster/WMF preview beats MathType OLE .bin."""
    path = (rel_map.get(rid) or "").replace("\\", "/").lower()
    name = path.rsplit("/", 1)[-1]
    ext = Path(name).suffix
    if ext in _DISPLAY_EXTS:
        return 0
    if "oleobject" in name or ext == ".bin" or "/embeddings/" in path:
        return 2
    return 1


def prefer_display_rids(rids: list[str], rel_map: dict[str, str]) -> list[str]:
    """
    One MathType object often has both a VML/WMF preview and an OLE .bin.
    Keep a single displayable rid so [[EQ:n]] maps to a browser-usable image.
    """
    if not rids:
        return []
    # preserve first-seen order among equal scores
    uniq: list[str] = []
    seen: set[str] = set()
    for rid in rids:
        if rid and rid not in seen:
            seen.add(rid)
            uniq.append(rid)
    best = min(_media_rid_score(r, rel_map) for r in uniq)
    chosen = [r for r in uniq if _media_rid_score(r, rel_map) == best]
    # One placeholder per drawing/object: prefer first display image
    if best == 0:
        return chosen[:1]
    return chosen[:1]


def extract_docx_exam(
    path: Path | str,
    *,
    media_dir: Path | str | None = None,
    ingest_id: str | None = None,
) -> dict[str, Any]:
    """
    Extract paragraph text in order; replace drawings/OLE with [[EQ:n]] placeholders.

    Returns:
      text, media (list of {eq_id, filename, path, content_type}),
      eq_count, warnings, ingest_id
    """
    src = Path(path)
    if not src.is_file():
        raise FileNotFoundError(str(src))
    iid = (ingest_id or uuid.uuid4().hex[:12]).strip()
    warnings: list[str] = []
    media_out: list[dict[str, Any]] = []
    eq_counter = 0
    rid_to_eq: dict[str, str] = {}

    dest_root: Path | None = None
    if media_dir is not None:
        dest_root = Path(media_dir) / iid
        dest_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(src, "r") as zf:
        rel_map = _load_rel_map(zf)
        try:
            doc_xml = zf.read("word/document.xml")
        except KeyError as e:
            raise ValueError("invalid_docx_missing_document") from e
        root = ET.fromstring(doc_xml)

        def ensure_eq(rid: str) -> str:
            nonlocal eq_counter
            if rid in rid_to_eq:
                return rid_to_eq[rid]
            eq_counter += 1
            eq_id = str(eq_counter)
            rid_to_eq[rid] = eq_id
            media_path = rel_map.get(rid)
            entry: dict[str, Any] = {
                "eq_id": eq_id,
                "rid": rid,
                "filename": "",
                "rel_path": media_path or "",
                "saved_as": "",
            }
            if media_path and media_path in zf.namelist() and dest_root is not None:
                raw_name = Path(media_path).name
                # stable name: eq_{n}_{original}
                saved = f"eq_{eq_id}_{raw_name}"
                target = dest_root / saved
                with zf.open(media_path) as src_f, open(target, "wb") as dst_f:
                    shutil.copyfileobj(src_f, dst_f)
                entry["filename"] = raw_name
                entry["saved_as"] = saved
                entry["path"] = str(target)
                # optional WMF→PNG via Pillow (best-effort)
                if raw_name.lower().endswith((".wmf", ".emf")):
                    png_name = f"eq_{eq_id}.png"
                    png_path = dest_root / png_name
                    if _try_wmf_to_png(target, png_path):
                        entry["saved_as"] = png_name
                        entry["path"] = str(png_path)
                        entry["converted"] = "png"
                    else:
                        warnings.append(f"wmf_keep_raw:eq_{eq_id}")
            elif media_path and dest_root is None:
                entry["filename"] = Path(media_path).name
            elif not media_path:
                warnings.append(f"missing_rel:{rid}")
            media_out.append(entry)
            return eq_id

        para_texts: list[str] = []
        for p in root.iter(f"{W}p"):
            # Only process body paragraphs; skip nested p inside tables later via iter —
            # still OK for exam papers (formulas mostly in body).
            parts: list[str] = []
            emitted_objects: set[int] = set()

            def walk(node: ET.Element) -> None:
                nonlocal eq_counter
                tag = _local(node.tag)
                if node.tag == f"{W}t" and (node.text or ""):
                    parts.append(node.text or "")
                    return
                if tag in {"drawing", "object", "pict"}:
                    oid = id(node)
                    if oid in emitted_objects:
                        return
                    emitted_objects.add(oid)
                    rids = prefer_display_rids(_collect_media_rids(node), rel_map)
                    if not rids:
                        eq_counter += 1
                        eq_id = str(eq_counter)
                        media_out.append(
                            {
                                "eq_id": eq_id,
                                "rid": "",
                                "filename": "",
                                "rel_path": "",
                                "saved_as": "",
                            }
                        )
                        parts.append(f"[[EQ:{eq_id}]]")
                    else:
                        # Single placeholder per shape (preview image preferred over OLE)
                        eq_id = ensure_eq(rids[0])
                        parts.append(f"[[EQ:{eq_id}]]")
                    return
                for ch in list(node):
                    walk(ch)

            for child in list(p):
                walk(child)

            line = "".join(parts).strip()
            if line:
                para_texts.append(line)

    text = "\n".join(para_texts)
    if eq_counter == 0:
        warnings.append("no_embedded_equations_found")
    return {
        "text": text,
        "media": media_out,
        "eq_count": eq_counter,
        "warnings": warnings,
        "ingest_id": iid,
    }


def resolve_eq_media_file(
    media_root: Path | str,
    ingest_id: str,
    eq_id: str | int,
) -> Path | None:
    """Find displayable ``eq_{n}.png`` / raster under media_root/ingest_id.

    Skips MathType OLE ``.bin`` — browsers cannot render them.
    """
    safe_id = "".join(c for c in str(ingest_id) if c.isalnum() or c in "-_")
    n = str(eq_id).strip()
    if not safe_id or not n.isdigit():
        return None
    folder = Path(media_root) / safe_id
    if not folder.is_dir():
        return None
    prefer = folder / f"eq_{n}.png"
    if prefer.is_file():
        return prefer
    matches = sorted(folder.glob(f"eq_{n}_*")) + sorted(folder.glob(f"eq_{n}.*"))
    raster = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    for p in matches:
        if p.is_file() and p.suffix.lower() in raster:
            return p
    # WMF/EMF: usable if Pillow (Windows) can open; still better than OLE
    for p in matches:
        if p.is_file() and p.suffix.lower() in {".wmf", ".emf"}:
            return p
    return None


def _try_wmf_to_png(src: Path, dest: Path) -> bool:
    try:
        from PIL import Image  # type: ignore

        with Image.open(src) as im:
            im.convert("RGBA").save(dest, format="PNG")
        return dest.is_file()
    except Exception:
        return False


def default_exam_media_root() -> Path:
    try:
        from config import settings

        base = Path(getattr(settings, "data_dir", None) or Path("data"))
    except Exception:
        base = Path("data")
    # prefer next to exam db if available
    try:
        from config import settings as s

        db = Path(getattr(s, "exam_bank_db_path", "") or "")
        if db.parent:
            return db.parent / "exam_media"
    except Exception:
        pass
    return base / "exam_media"
