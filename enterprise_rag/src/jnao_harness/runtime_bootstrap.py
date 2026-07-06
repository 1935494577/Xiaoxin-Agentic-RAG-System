"""Bootstrap Jnao LangGraph runtime on Jnao FastAPI lifespan."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from jnao_harness.paths import repo_root
from jnao_harness.runtime_handles import HarnessRuntime, set_runtime

logger = logging.getLogger(__name__)


def _ensure_harness_env() -> None:
    root = repo_root()
    os.environ.setdefault("DEER_FLOW_PROJECT_ROOT", str(root))
    os.environ.setdefault("DEER_FLOW_CONFIG_PATH", str(root / "config.yaml"))
    os.environ.setdefault("DEER_FLOW_EXTENSIONS_CONFIG_PATH", str(root / "extensions_config.json"))
    data_dir = root / ".deer-flow" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def harness_runtime_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize agent harness runtime singletons; no-op when harness is not installed."""
    try:
        import deerflow  # noqa: F401 — upstream harness package name
    except ImportError:
        logger.info("Agent harness not installed — skipping runtime bootstrap")
        set_runtime(None)
        yield
        return

    _ensure_harness_env()
    from deerflow.config.app_config import AppConfig
    from deerflow.persistence.engine import close_engine, get_session_factory, init_engine_from_config
    from deerflow.runtime import RunManager, make_store, make_stream_bridge
    from deerflow.runtime.checkpointer.async_provider import make_checkpointer
    from deerflow.runtime.events.store import make_run_event_store
    from deerflow.persistence.thread_meta import make_thread_store

    startup_config = AppConfig.from_file(os.environ["DEER_FLOW_CONFIG_PATH"])
    async with AsyncExitStack() as stack:
        app.state.stream_bridge = await stack.enter_async_context(make_stream_bridge(startup_config))
        await init_engine_from_config(startup_config.database)
        app.state.checkpointer = await stack.enter_async_context(make_checkpointer(startup_config))
        app.state.store = await stack.enter_async_context(make_store(startup_config))

        sf = get_session_factory()
        if sf is not None:
            from deerflow.persistence.run import RunRepository

            app.state.run_store = RunRepository(sf)
        else:
            from deerflow.runtime.runs.store.memory import MemoryRunStore

            app.state.run_store = MemoryRunStore()

        app.state.thread_store = make_thread_store(sf, app.state.store)
        run_events_config = getattr(startup_config, "run_events", None)
        app.state.run_events_config = run_events_config
        app.state.run_event_store = make_run_event_store(run_events_config)
        app.state.run_manager = RunManager(store=app.state.run_store)

        from jnao_harness.runtime_handles import runtime_from_app_state

        set_runtime(runtime_from_app_state(app))
        logger.info("Jnao runtime bootstrap OK")

        channel_service = None
        try:
            from app.channels.service import start_channel_service

            channel_service = await start_channel_service(startup_config)
            app.state.channel_service = channel_service
            logger.info("Channel service: %s", channel_service.get_status())
        except Exception:
            logger.info("Channel service not started (no credentials or harness optional deps missing)")

        try:
            yield
        finally:
            try:
                from app.channels.service import stop_channel_service

                await stop_channel_service()
            except Exception:
                pass
            run_manager = getattr(app.state, "run_manager", None)
            if run_manager is not None:
                try:
                    await run_manager.shutdown(timeout=5.0)
                except Exception:
                    logger.exception("Jnao run manager shutdown failed")
            await close_engine()
            set_runtime(None)
