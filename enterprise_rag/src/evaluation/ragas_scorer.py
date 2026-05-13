"""步骤8：RAGAS 离线评估；读取 enterprise_rag/data/eval/golden.jsonl。RAGAS 不可用时回退简单指标。"""

from __future__ import annotations

import json
import math
from pathlib import Path

from config import settings


def _eval_dir() -> Path:
    return settings.data_raw_dir.parent / "eval"


def _load_golden(path: Path) -> dict[str, list]:
    rows: dict[str, list] = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows["question"].append(obj["question"])
            rows["answer"].append(obj.get("answer", ""))
            ctx = obj.get("contexts")
            if isinstance(ctx, str):
                ctx = [ctx]
            rows["contexts"].append(list(ctx or []))
            rows["ground_truth"].append(obj.get("ground_truth", ""))
    return rows


def _naive_metrics(rows: dict[str, list]) -> dict[str, float]:
    """不依赖 LLM 的粗指标：答案是否被上下文子串覆盖（仅作流水线自检）。"""
    hits = 0
    n = 0
    for ans, ctxs in zip(rows["answer"], rows["contexts"]):
        n += 1
        a = (ans or "").strip().lower()
        if not a:
            continue
        ok = False
        for c in ctxs:
            piece = (c or "").strip().lower()
            if len(piece) >= 8 and piece in a:
                ok = True
                break
            if len(a) >= 8 and a[: min(len(a), 64)] in piece:
                ok = True
                break
        if ok:
            hits += 1
    return {"naive_context_answer_overlap_rate": hits / n if n else 0.0, "rows": float(n)}


def score_rag_batch(dataset_rows: dict[str, list]) -> dict:
    """优先 RAGAS；导入或运行失败时回退 naive 指标（保证离线命令可跑通）。"""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, faithfulness

        ds = Dataset.from_dict(dataset_rows)
        out = evaluate(dataset=ds, metrics=[faithfulness, answer_relevancy])
        scores = getattr(out, "scores", None)
        if isinstance(scores, dict):
            out_dict: dict[str, float] = {}
            for k, v in scores.items():
                try:
                    out_dict[str(k)] = float(v)  # type: ignore[arg-type]
                except Exception:
                    try:
                        out_dict[str(k)] = float(v.item())  # type: ignore[union-attr]
                    except Exception:
                        out_dict[str(k)] = 0.0
            return out_dict
        return {"ragas_debug": repr(out)}
    except Exception as e:
        m = _naive_metrics(dataset_rows)
        m["ragas_error"] = str(e)
        m["mode"] = "fallback_naive"
        return m


def main() -> int:
    eval_dir = _eval_dir()
    eval_dir.mkdir(parents=True, exist_ok=True)
    golden = eval_dir / "golden.jsonl"
    example = eval_dir / "golden.example.jsonl"

    if not golden.exists():
        print(f"Missing golden file: {golden}")
        print(f"Copy example: copy {example} {golden}   (PowerShell: Copy-Item)")
        return 0

    rows = _load_golden(golden)
    if not rows["question"]:
        print("golden.jsonl has no rows.")
        return 0

    if not settings.openai_api_key:
        print("OPENAI_API_KEY not set: skip LLM-based RAGAS; printing naive metrics only.")
        out = _naive_metrics(rows)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"Loaded {len(rows['question'])} golden rows ...")
    out = score_rag_batch(rows)
    # 将不可 JSON 的值转为 float
    safe: dict[str, object] = {}
    for k, v in out.items():
        if hasattr(v, "item") and not isinstance(v, (bytes, str)):
            try:
                safe[k] = float(v)  # type: ignore[arg-type]
            except Exception:
                safe[k] = str(v)
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            safe[k] = None
        else:
            safe[k] = v
    print(json.dumps(safe, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
