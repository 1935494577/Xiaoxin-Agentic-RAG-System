"""LangSmith / LangChain tracing (optional, driven by env)."""

import os


def configure_tracing() -> None:
    # LangChain reads LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY, LANGCHAIN_PROJECT from the environment.
    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1", "yes"):
        try:
            import langsmith  # noqa: F401
        except ImportError:
            pass
    return None
