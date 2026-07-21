"""Shared Jnao runtime singletons (populated on FastAPI lifespan)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HarnessRuntime:
    stream_bridge: Any
    run_manager: Any
    run_store: Any
    checkpointer: Any
    run_event_store: Any
    run_events_config: Any
    thread_store: Any
    store: Any | None = None


_runtime: HarnessRuntime | None = None


def get_runtime() -> HarnessRuntime | None:
    return _runtime


def set_runtime(runtime: HarnessRuntime | None) -> None:
    global _runtime
    _runtime = runtime


def runtime_from_app_state(app: Any) -> HarnessRuntime | None:
    bridge = getattr(app.state, "stream_bridge", None)
    run_manager = getattr(app.state, "run_manager", None)
    run_store = getattr(app.state, "run_store", None)
    checkpointer = getattr(app.state, "checkpointer", None)
    if not all((bridge, run_manager, run_store, checkpointer)):
        return None
    return HarnessRuntime(
        stream_bridge=bridge,
        run_manager=run_manager,
        run_store=run_store,
        checkpointer=checkpointer,
        run_event_store=getattr(app.state, "run_event_store", None),
        run_events_config=getattr(app.state, "run_events_config", None),
        thread_store=getattr(app.state, "thread_store", None),
        store=getattr(app.state, "store", None),
    )
