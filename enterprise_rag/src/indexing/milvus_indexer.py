from __future__ import annotations

from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from config import settings
from indexing.embeddings import embedding_dim
from chunker.utils import tags_to_store_value
from security.access_control import milvus_access_expr

_backend: str | None = None
_lite_started = False
_atexit_registered = False
_collection_cache: Collection | None = None
_collection_cache_name: str | None = None


def _get_backend() -> str:
    """remote | lite | numpy（由活动向量库配置决定）。"""
    global _backend
    if _backend is not None:
        return _backend
    try:
        from api.vector_store_registry import (
            BACKEND_MILVUS_LITE,
            BACKEND_MILVUS_REMOTE,
            BACKEND_NUMPY,
            get_active_backend,
        )

        chosen = get_active_backend()
        if chosen == BACKEND_NUMPY:
            _backend = "numpy"
            return _backend
        if chosen == BACKEND_MILVUS_REMOTE:
            _backend = "remote"
            return _backend
        if chosen == BACKEND_MILVUS_LITE:
            try:
                import milvus  # noqa: F401

                _backend = "lite"
            except ImportError:
                _backend = "numpy"
            return _backend
    except Exception:
        pass
    if not settings.use_milvus_lite:
        _backend = "remote"
        return _backend
    try:
        import milvus  # noqa: F401

        _backend = "lite"
    except ImportError:
        _backend = "numpy"
    return _backend


def reload_vector_backend() -> None:
    global _backend, _collection_cache, _collection_cache_name
    _backend = None
    _collection_cache = None
    _collection_cache_name = None


def count_vectors_for_collection(collection: str, *, backend: str | None = None) -> tuple[int, int | None]:
    """Return (count, dim) for status display."""
    if backend == "numpy" or _get_backend() == "numpy":
        from indexing.numpy_vector_index import vector_count_and_dim

        return vector_count_and_dim()
    _connect()
    name = collection or _active_collection_name()
    if not utility.has_collection(name):
        return 0, None
    col = Collection(name)
    col.load()
    count = col.num_entities
    dim = None
    for f in col.schema.fields:
        if f.name == "vector":
            dim = int(f.params.get("dim") or 0) or None
            break
    return int(count), dim


def _active_collection_name() -> str:
    try:
        from api.vector_store_registry import get_active_milvus_collection

        return get_active_milvus_collection()
    except Exception:
        return settings.milvus_collection


def get_vector_backend() -> str:
    return _get_backend()


def _start_milvus_lite() -> None:
    global _lite_started, _atexit_registered
    if _lite_started or _get_backend() != "lite":
        return
    from pathlib import Path

    from milvus import default_server

    base = Path(settings.milvus_lite_data_dir)
    base.mkdir(parents=True, exist_ok=True)
    default_server.set_base_dir(str(base))
    default_server.start()
    alias = "default"
    if not connections.has_connection(alias):
        connections.connect(alias=alias, host="127.0.0.1", port=str(default_server.listen_port))
    _lite_started = True
    if not _atexit_registered:
        import atexit

        atexit.register(shutdown_vector_db)
        _atexit_registered = True


def shutdown_vector_db() -> None:
    global _lite_started
    if not _lite_started or _get_backend() != "lite":
        return
    try:
        from milvus import default_server

        default_server.stop()
    except Exception:
        pass
    try:
        connections.disconnect("default")
    except Exception:
        pass
    _lite_started = False


def init_vector_db() -> None:
    _connect()
    if _get_backend() == "numpy":
        from indexing.numpy_vector_index import init_store

        init_store()


def _connect() -> None:
    if _get_backend() == "numpy":
        return
    alias = "default"
    if connections.has_connection(alias):
        return
    if _get_backend() == "lite":
        _start_milvus_lite()
        return
    connections.connect(alias=alias, host=settings.milvus_host, port=str(settings.milvus_port))


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _collection_has_field(col: Collection, name: str) -> bool:
    return any(f.name == name for f in col.schema.fields)


def ensure_collection() -> Collection:
    if _get_backend() == "numpy":
        raise RuntimeError("ensure_collection() not used in numpy vector mode")
    global _collection_cache, _collection_cache_name
    name = _active_collection_name()
    if _collection_cache is not None and _collection_cache_name == name:
        _collection_cache.load()
        return _collection_cache
    _connect()
    dim = embedding_dim()
    if utility.has_collection(name):
        col = Collection(name)
        col.load()
        existing_dim = None
        for f in col.schema.fields:
            if f.name == "vector":
                existing_dim = int(f.params.get("dim") or 0) or None
                break
        if existing_dim and existing_dim != dim:
            raise ValueError(
                f"Milvus 集合 {name} 为 {existing_dim} 维，当前嵌入模型为 {dim} 维。"
                "请新建并切换到匹配的向量库。"
            )
        _collection_cache = col
        _collection_cache_name = name
        return col

    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=128),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="parent_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="department", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="permission_label", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=512),
    ]
    schema = CollectionSchema(fields, description="child chunk vectors")
    col = Collection(name, schema)
    idx = {"index_type": "IVF_FLAT", "metric_type": "IP", "params": {"nlist": 1024}}
    col.create_index(field_name="vector", index_params=idx)
    col.load()
    _collection_cache = col
    _collection_cache_name = name
    return col


def delete_by_source(source: str) -> None:
    if _get_backend() == "numpy":
        from indexing.numpy_vector_index import delete_by_source as np_del

        np_del(source)
        return
    _connect()
    name = _active_collection_name()
    if not utility.has_collection(name):
        return
    col = Collection(name)
    col.load()
    col.delete(expr=f'source == "{_esc(source)}"')
    col.flush()


def insert_child_vectors(
    ids: list[str],
    vectors: list[list[float]],
    texts: list[str],
    parent_ids: list[str],
    departments: list[str],
    sources: list[str],
    tags: list[str] | None = None,
    permission_labels: list[str] | None = None,
) -> None:
    if _get_backend() == "numpy":
        from indexing.numpy_vector_index import insert_child_vectors as np_ins

        np_ins(
            ids,
            vectors,
            texts,
            parent_ids,
            departments,
            sources,
            tags=tags,
            permission_labels=permission_labels,
        )
        return
    try:
        from api.vector_store_registry import validate_insert_vectors

        validate_insert_vectors(vectors)
    except ImportError:
        pass
    col = ensure_collection()
    texts_t = [t[:1990] for t in texts]
    tag_str = tags_to_store_value(tags)
    perms = permission_labels or ["internal"] * len(ids)
    entities: list[Any] = [ids, vectors, texts_t, parent_ids, departments]
    if _collection_has_field(col, "permission_label"):
        entities.append([perms[i] if i < len(perms) else "internal" for i in range(len(ids))])
    entities.append(sources)
    if _collection_has_field(col, "tags"):
        entities.append([tag_str] * len(ids))
    col.insert(entities)
    col.flush()
    col.load()


def vector_search(
    query_vector: list[float],
    top_k: int,
    user_department: str | None = None,
) -> list[dict[str, Any]]:
    if _get_backend() == "numpy":
        from indexing.numpy_vector_index import vector_search as np_search

        return np_search(query_vector, top_k, user_department=user_department)
    try:
        from api.vector_store_registry import assert_search_compatible

        assert_search_compatible(len(query_vector))
    except ImportError:
        pass
    col = ensure_collection()
    search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
    output_fields = ["id", "parent_id", "department", "source", "text"]
    if _collection_has_field(col, "permission_label"):
        output_fields.append("permission_label")
    if _collection_has_field(col, "tags"):
        output_fields.append("tags")
    kw: dict[str, Any] = dict(
        data=[query_vector],
        anns_field="vector",
        param=search_params,
        limit=top_k,
        output_fields=output_fields,
    )
    if user_department:
        expr = milvus_access_expr(
            user_department,
            has_permission_field=_collection_has_field(col, "permission_label"),
        )
        if expr:
            kw["expr"] = expr
    res = col.search(**kw)
    hits: list[dict[str, Any]] = []
    for hit in res[0]:
        row = {
            "id": hit.entity.get("id"),
            "parent_id": hit.entity.get("parent_id"),
            "department": hit.entity.get("department"),
            "source": hit.entity.get("source"),
            "text": hit.entity.get("text"),
            "score": float(hit.distance),
        }
        if "permission_label" in output_fields:
            row["permission_label"] = hit.entity.get("permission_label") or ""
        if "tags" in output_fields:
            row["tags"] = hit.entity.get("tags") or ""
        hits.append(row)
    return hits
