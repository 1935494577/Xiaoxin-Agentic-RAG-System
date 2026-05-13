import json
from pathlib import Path

import pytest


def test_naive_metrics_overlap():
    from evaluation.ragas_scorer import _naive_metrics

    rows = {
        "question": ["q"],
        "answer": ["LangGraph orchestrates steps"],
        "contexts": [["LangGraph orchestrates rewrite, retrieve, rerank, and generate steps."]],
        "ground_truth": ["LangGraph"],
    }
    m = _naive_metrics(rows)
    assert m["rows"] == 1.0
    assert m["naive_context_answer_overlap_rate"] >= 0.0


def test_golden_example_jsonl_is_valid():
    root = Path(__file__).resolve().parents[1]
    p = root / "enterprise_rag" / "data" / "eval" / "golden.example.jsonl"
    line = p.read_text(encoding="utf-8").strip().splitlines()[0]
    obj = json.loads(line)
    assert "question" in obj and "contexts" in obj
