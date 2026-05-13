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

_backend: str | None = None
_lite_started = False
_atexit_registered = False


def _get_backend() -> str:
    """remote | lite | numpy（无 Docker：lite 优先；Windows 无 milvus-lite 轮子时用 numpy）。"""
    global _backend
    if _backend is not None:
        return _backend
    if not settings.use_milvus_lite:
        _backend = "remote"
        return _backend
    try:
        import milvus  # noqa: F401

        _backend = "lite"
    except ImportError:
        _backend = "numpy"
    return _backend


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


def ensure_collection() -> Collection:
    if _get_backend() == "numpy":
        raise RuntimeError("ensure_collection() not used in numpy vector mode")
    _connect()
    name = settings.milvus_collection
    dim = embedding_dim()
    if utility.has_collection(name):
        col = Collection(name)
        col.load()
        return col

    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=128),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000),
        FieldSchema(name="parent_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="department", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=1024),
    ]
    schema = CollectionSchema(fields, description="child chunk vectors")
    col = Collection(name, schema)
    idx = {"index_type": "IVF_FLAT", "metric_type": "IP", "params": {"nlist": 1024}}
    col.create_index(field_name="vector", index_params=idx)
    col.load()
    return col


def delete_by_source(source: str) -> None:
    if _get_backend() == "numpy":
        from indexing.numpy_vector_index import delete_by_source as np_del

        np_del(source)
        return
    _connect()
    name = settings.milvus_collection
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
) -> None:
    if _get_backend() == "numpy":
        from indexing.numpy_vector_index import insert_child_vectors as np_ins

        np_ins(ids, vectors, texts, parent_ids, departments, sources)
        return
    col = ensure_collection()
    texts_t = [t[:1990] for t in texts]
    entities = [ids, vectors, texts_t, parent_ids, departments, sources]
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
    col = ensure_collection()
    col.load()
    search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
    kw: dict[str, Any] = dict(
        data=[query_vector],
        anns_field="vector",
        param=search_params,
        limit=top_k,
        output_fields=["id", "parent_id", "department", "source", "text"],
    )
    if user_department:
        kw["expr"] = f'department == "{_esc(user_department)}"'
    res = col.search(**kw)
    hits: list[dict[str, Any]] = []
    for hit in res[0]:
        hits.append(
            {
                "id": hit.entity.get("id"),
                "parent_id": hit.entity.get("parent_id"),
                "department": hit.entity.get("department"),
                "source": hit.entity.get("source"),
                "text": hit.entity.get("text"),
                "score": float(hit.distance),
            }
        )
    return hits
