"""Regression: config.yaml must not pass api_base into ChatOpenAI model_kwargs."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "enterprise_rag" / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))


@pytest.mark.harness
def test_chat_model_does_not_forward_api_base_to_openai_sdk():
    pytest.importorskip("deerflow")
    from langchain_core.messages import HumanMessage

    from deerflow.config.app_config import AppConfig
    from deerflow.models.factory import create_chat_model

    cfg = AppConfig.from_file(str(ROOT / "config.yaml"))
    dumped = cfg.models[0].model_dump(exclude_none=True)
    assert "api_base" not in dumped, "api_base leaks into OpenAI SDK as model_kwargs"

    if not os.environ.get("OPENAI_API_KEY", "").strip():
        pytest.skip("OPENAI_API_KEY not set")

    model = create_chat_model(app_config=cfg, attach_tracing=False)
    assert "api_base" not in (getattr(model, "model_kwargs", None) or {})

    import asyncio

    async def _invoke() -> None:
        await model.ainvoke([HumanMessage(content="reply with exactly: ok")])

    asyncio.run(_invoke())
