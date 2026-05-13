from evaluation.langsmith_trace import configure_tracing

__all__ = ["configure_tracing", "score_rag_batch"]


def __getattr__(name: str):
    if name == "score_rag_batch":
        from evaluation.ragas_scorer import score_rag_batch as _score

        return _score
    raise AttributeError(name)
