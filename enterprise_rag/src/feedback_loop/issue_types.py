"""Feedback issue taxonomy and handling hints (Sprint B)."""

from __future__ import annotations

ISSUE_TYPES: tuple[str, ...] = (
    "retrieval_miss",
    "hallucination",
    "stale_doc",
    "prompt",
    "tone",
    "ok",
)

ISSUE_LABELS: dict[str, str] = {
    "retrieval_miss": "检索未命中",
    "hallucination": "幻觉 / 与资料不符",
    "stale_doc": "文档过时",
    "prompt": "提示词 / 生成策略",
    "tone": "语气 / 表达",
    "ok": "无问题 / 正向",
}

# 运营处理策略（文档化；Sprint C Actuator 将对接）
ISSUE_STRATEGIES: dict[str, str] = {
    "retrieval_miss": "检查知识库是否缺文档；调低 kb_min_score；补入库后重跑检索评测。",
    "hallucination": "加强 verifier；收紧 KB 提示词；将坏例加入 golden。",
    "stale_doc": "触发对应 source 重入库；更新制度版本。",
    "prompt": "调整 persona / KB 系统提示词槽位；A/B 对比 faithfulness。",
    "tone": "调整 persona 语气；一般无需改索引。",
    "ok": "归档；可用于扩充正向 golden（低优先级）。",
}

SEVERITIES: tuple[str, ...] = ("low", "medium", "high")

STATUSES: tuple[str, ...] = (
    "pending",
    "triaged",
    "approved",
    "applied",
    "rejected",
    "evaluated",
)


def issue_type_label(issue_type: str | None) -> str:
    if not issue_type:
        return "未分类"
    return ISSUE_LABELS.get(issue_type, issue_type)
