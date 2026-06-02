"""需从仓库根目录运行 pytest，且 PYTHONPATH 含 enterprise_rag/src。"""

import pytest
from fastapi.testclient import TestClient


def test_public_config_and_preview():
    try:
        from api.main import app  # noqa: PLC0415
    except ModuleNotFoundError as e:
        pytest.skip(f"API 依赖未就绪: {e}")

    with TestClient(app) as client:
        r = client.get("/config/public")
        assert r.status_code == 200
        body = r.json()
        assert "embedding_model" in body
        assert "default_chat_model" in body

        r2 = client.post("/ingest/preview", json={"text": "  hello\nworld  ", "use_presidio": False})
        assert r2.status_code == 200
        assert "hello" in r2.json().get("cleaned", "")

        r3 = client.get("/", follow_redirects=False)
        assert r3.status_code in (301, 302, 303, 307, 308)
        assert r3.headers.get("location", "").rstrip("/").endswith("/docs")

        r4 = client.get("/favicon.ico")
        assert r4.status_code == 204

        r5 = client.get("/config/model-profiles")
        assert r5.status_code == 200
        assert "profiles" in r5.json()


def test_ingest_upload_rejects_path_traversal():
    try:
        from api.main import app  # noqa: PLC0415
    except ModuleNotFoundError as e:
        pytest.skip(f"API 依赖未就绪: {e}")

    with TestClient(app) as client:
        r = client.post(
            "/ingest/upload",
            files={"file": ("../../evil.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400
