import uuid


def new_chunk_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def normalize_ingest_tags(raw: str | list[str] | None) -> list[str]:
    """Strip, dedupe, and cap user-supplied ingest tags."""
    if raw is None:
        return []
    parts: list[str]
    if isinstance(raw, str):
        parts = raw.replace("，", ",").split(",")
    else:
        parts = [str(x) for x in raw]
    out: list[str] = []
    seen: set[str] = set()
    for item in parts:
        t = str(item).strip()
        if not t:
            continue
        t = t[:32]
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
        if len(out) >= 20:
            break
    return out


def tags_to_store_value(tags: list[str] | None) -> str:
    return ",".join(normalize_ingest_tags(tags))


def tags_from_store_value(raw: str | None) -> list[str]:
    if not raw:
        return []
    return normalize_ingest_tags(str(raw).split(","))


def parent_child_metadata(
    parent_id: str,
    source: str,
    department: str,
    permission_label: str,
    child_index: int,
    tags: list[str] | None = None,
) -> dict:
    return {
        "parent_id": parent_id,
        "source": source,
        "department": department,
        "permission_label": permission_label,
        "child_index": child_index,
        "tags": normalize_ingest_tags(tags),
    }
