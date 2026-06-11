"""Named vector store profiles — backend, paths, embedding metadata, active selection."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings

from indexing.embeddings import known_embedding_dim

BACKEND_NUMPY = "numpy"
BACKEND_MILVUS_LITE = "milvus_lite"
BACKEND_MILVUS_REMOTE = "milvus_remote"
BACKEND_LABELS = {
    BACKEND_NUMPY: "NumPy 文件（本地，无需 Docker）",
    BACKEND_MILVUS_LITE: "Milvus Lite（嵌入式）",
    BACKEND_MILVUS_REMOTE: "Milvus 远程服务",
}

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _registry_path() -> Path:
    return Path(settings.vector_stores_registry_path)


def _stores_dir() -> Path:
    d = Path(settings.vector_stores_data_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _abs_path(rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute():
        return p
    return (_REPO_ROOT / p).resolve()


def _rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(_REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def available_backends() -> list[str]:
    out = [BACKEND_NUMPY]
    if settings.use_milvus_lite:
        try:
            import milvus  # noqa: F401

            out.append(BACKEND_MILVUS_LITE)
        except ImportError:
            pass
    else:
        out.append(BACKEND_MILVUS_REMOTE)
    return out


def _default_backend() -> str:
    opts = available_backends()
    if BACKEND_NUMPY in opts:
        return BACKEND_NUMPY
    return opts[0]


def load_registry() -> dict[str, Any]:
    path = _registry_path()
    if not path.is_file():
        return {"stores": [], "active_store_id": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"stores": [], "active_store_id": None}
        stores = data.get("stores")
        if not isinstance(stores, list):
            stores = []
        return {"stores": stores, "active_store_id": data.get("active_store_id")}
    except Exception:
        return {"stores": [], "active_store_id": None}


def save_registry(data: dict[str, Any]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _count_numpy_vectors(path: Path) -> tuple[int, int | None]:
    if not path.is_file():
        return 0, None
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list) or not rows:
            return 0, None
        dim = len(rows[0].get("vector") or [])
        return len(rows), dim or None
    except Exception:
        return 0, None


def _count_bm25_docs(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return len(data.get("corpus") or [])
    except Exception:
        return 0


def _current_embedding_meta() -> tuple[str, int]:
    model = settings.embedding_model.strip()
    dim = known_embedding_dim(model)
    if dim is None:
        from indexing.embeddings import embedding_dim

        dim = int(embedding_dim())
    return model, dim


def store_status(store: dict[str, Any]) -> dict[str, Any]:
    backend = str(store.get("backend") or BACKEND_NUMPY)
    model = str(store.get("embedding_model") or "")
    dim = store.get("embedding_dim")
    vector_count = 0
    stored_dim: int | None = None
    bm25_docs = 0

    if backend == BACKEND_NUMPY:
        np_path = _abs_path(str(store.get("numpy_path") or ""))
        vector_count, stored_dim = _count_numpy_vectors(np_path)
        bm25_docs = _count_bm25_docs(_abs_path(str(store.get("bm25_path") or "")))
    else:
        bm25_docs = _count_bm25_docs(_abs_path(str(store.get("bm25_path") or "")))
        active = get_active_store()
        if str(active.get("id")) == str(store.get("id")):
            try:
                from indexing.milvus_indexer import count_vectors_for_collection

                coll = str(store.get("milvus_collection") or "")
                vector_count, stored_dim = count_vectors_for_collection(coll, backend=backend)
            except Exception:
                vector_count, stored_dim = 0, store.get("embedding_dim")
        else:
            vector_count = 0
            stored_dim = store.get("embedding_dim")

    if stored_dim is not None:
        dim = stored_dim
    cur_model, cur_dim = _current_embedding_meta()
    compatible = stored_dim is None or stored_dim == 0 or stored_dim == cur_dim

    return {
        "vector_count": vector_count,
        "bm25_docs": bm25_docs,
        "embedding_dim": dim,
        "stored_dim": stored_dim,
        "embedding_model": model,
        "current_embedding_model": cur_model,
        "current_embedding_dim": cur_dim,
        "compatible": compatible,
        "backend": backend,
        "backend_label": BACKEND_LABELS.get(backend, backend),
    }


def _public_store(store: dict[str, Any], *, active: bool) -> dict[str, Any]:
    st = store_status(store)
    return {
        "id": store.get("id"),
        "name": store.get("name"),
        "backend": store.get("backend"),
        "backend_label": st["backend_label"],
        "embedding_model": store.get("embedding_model"),
        "embedding_dim": st.get("embedding_dim"),
        "numpy_path": store.get("numpy_path") or "",
        "bm25_path": store.get("bm25_path") or "",
        "milvus_collection": store.get("milvus_collection") or "",
        "vector_count": st["vector_count"],
        "bm25_docs": st["bm25_docs"],
        "compatible": st["compatible"],
        "current_embedding_model": st["current_embedding_model"],
        "current_embedding_dim": st["current_embedding_dim"],
        "active": active,
        "created_at": store.get("created_at"),
        "updated_at": store.get("updated_at"),
    }


def list_stores_public() -> dict[str, Any]:
    reg = load_registry()
    active_id = reg.get("active_store_id")
    stores = reg.get("stores") or []
    public = [_public_store(s, active=s.get("id") == active_id) for s in stores]
    active = next((p for p in public if p.get("active")), None)
    return {
        "stores": public,
        "active_store_id": active_id,
        "active": active,
        "available_backends": [
            {"id": b, "label": BACKEND_LABELS.get(b, b), "available": b in available_backends()}
            for b in BACKEND_LABELS
        ],
    }


def get_store_by_id(store_id: str) -> dict[str, Any] | None:
    reg = load_registry()
    for s in reg.get("stores") or []:
        if str(s.get("id")) == store_id:
            return s
    return None


def get_active_store() -> dict[str, Any]:
    reg = load_registry()
    active_id = reg.get("active_store_id")
    stores = reg.get("stores") or []
    if active_id:
        for s in stores:
            if str(s.get("id")) == active_id:
                return s
    if stores:
        return stores[0]
    return {}


def get_active_numpy_path() -> Path:
    store = get_active_store()
    rel = str(store.get("numpy_path") or settings.numpy_vector_store_path)
    return _abs_path(rel)


def get_active_bm25_path() -> Path:
    store = get_active_store()
    rel = str(store.get("bm25_path") or settings.bm25_index_path)
    return _abs_path(rel)


def get_active_milvus_collection() -> str:
    store = get_active_store()
    return str(store.get("milvus_collection") or settings.milvus_collection)


def get_active_backend() -> str:
    store = get_active_store()
    return str(store.get("backend") or _default_backend())


def reload_all_indexes() -> None:
    from indexing.bm25_indexer import reload_bm25_index
    from indexing.milvus_indexer import get_vector_backend, reload_vector_backend

    reload_vector_backend()
    if get_vector_backend() == "numpy":
        from indexing.numpy_vector_index import reload_store

        reload_store()
    reload_bm25_index()


def ensure_default_registry() -> None:
    reg = load_registry()
    if reg.get("stores"):
        if not reg.get("active_store_id") and reg["stores"]:
            reg["active_store_id"] = reg["stores"][0]["id"]
            save_registry(reg)
        return

    model, dim = _current_embedding_meta()
    sid = uuid.uuid4().hex
    legacy_np = _rel_path(Path(settings.numpy_vector_store_path))
    legacy_bm25 = _rel_path(Path(settings.bm25_index_path))
    _, stored_dim = _count_numpy_vectors(_abs_path(legacy_np))
    store = {
        "id": sid,
        "name": "默认向量库",
        "backend": _default_backend(),
        "numpy_path": legacy_np,
        "bm25_path": legacy_bm25,
        "milvus_collection": settings.milvus_collection,
        "embedding_model": model,
        "embedding_dim": stored_dim or dim,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    reg = {"stores": [store], "active_store_id": sid}
    save_registry(reg)


def create_store(*, name: str, backend: str | None = None) -> dict[str, Any]:
    backend = (backend or _default_backend()).strip()
    if backend not in BACKEND_LABELS:
        raise ValueError(f"不支持的向量库类型: {backend}")
    if backend not in available_backends():
        raise ValueError(f"当前环境不可用 {BACKEND_LABELS.get(backend, backend)}")

    model, dim = _current_embedding_meta()
    sid = uuid.uuid4().hex[:12]
    safe_name = (name or f"{model.split('/')[-1]}-{dim}").strip()[:64] or f"store-{sid}"
    bm25_path = _rel_path(_stores_dir() / f"{sid}_bm25.json")

    store: dict[str, Any] = {
        "id": sid,
        "name": safe_name,
        "backend": backend,
        "bm25_path": bm25_path,
        "embedding_model": model,
        "embedding_dim": dim,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }

    if backend == BACKEND_NUMPY:
        np_path = _stores_dir() / f"{sid}_vectors.json"
        np_path.write_text("[]", encoding="utf-8")
        store["numpy_path"] = _rel_path(np_path)
    else:
        store["milvus_collection"] = f"vs_{sid}"
        store["numpy_path"] = ""

    reg = load_registry()
    reg.setdefault("stores", []).append(store)
    if not reg.get("active_store_id"):
        reg["active_store_id"] = sid
    save_registry(reg)
    return _public_store(store, active=reg.get("active_store_id") == sid)


def activate_store(store_id: str) -> dict[str, Any]:
    reg = load_registry()
    found = None
    for s in reg.get("stores") or []:
        if str(s.get("id")) == store_id:
            found = s
            break
    if not found:
        raise ValueError("向量库不存在")

    reg["active_store_id"] = store_id
    found["updated_at"] = _utc_now()
    save_registry(reg)
    reload_all_indexes()
    return _public_store(found, active=True)


def delete_store(store_id: str) -> None:
    reg = load_registry()
    if reg.get("active_store_id") == store_id:
        raise ValueError("无法删除当前使用中的向量库，请先切换到其他库")
    stores = [s for s in (reg.get("stores") or []) if str(s.get("id")) != store_id]
    if len(stores) == len(reg.get("stores") or []):
        raise ValueError("向量库不存在")
    reg["stores"] = stores
    save_registry(reg)


def validate_insert_vectors(vectors: list[list[float]]) -> None:
    if not vectors:
        return
    store = get_active_store()
    st = store_status(store)
    cur_dim = st["current_embedding_dim"]
    ins_dim = len(vectors[0])
    if ins_dim != cur_dim:
        raise ValueError(
            f"入库向量维度 {ins_dim} 与当前嵌入模型 {cur_dim} 维不一致。"
            f"请切换到匹配的向量库，或新建向量库后重新入库。"
        )
    stored_dim = st.get("stored_dim")
    if stored_dim and stored_dim != cur_dim:
        raise ValueError(
            f"当前向量库已存在 {stored_dim} 维数据，与嵌入模型 {cur_dim} 维不匹配。"
            f"请新建向量库并重新入库，避免检索出错。"
        )


def assert_search_compatible(query_dim: int) -> None:
    store = get_active_store()
    st = store_status(store)
    stored_dim = st.get("stored_dim")
    if stored_dim and stored_dim != query_dim:
        name = store.get("name") or store.get("id")
        raise ValueError(
            f"向量库「{name}」为 {stored_dim} 维，当前模型输出 {query_dim} 维。"
            f"请在「向量库设置」中切换或新建匹配的向量库后重新入库。"
        )
