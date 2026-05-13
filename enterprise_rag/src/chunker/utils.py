import uuid


def new_chunk_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def parent_child_metadata(parent_id: str, source: str, department: str, permission_label: str, child_index: int) -> dict:
    return {
        "parent_id": parent_id,
        "source": source,
        "department": department,
        "permission_label": permission_label,
        "child_index": child_index,
    }
