"""工具注册表：定义、启停、执行入口。"""

from __future__ import annotations

from typing import Any

from agent.tools.builtins import run_builtin
from agent.tools.config.store import load_json_config, save_json_config

TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "get_beijing_time": {
        "label": "北京时间",
        "description": (
            "获取当前北京时间（年月日、星期、时刻）。"
            "用户问今天几号、现在几点、星期几、哪年哪月时必须调用此工具，禁止自行猜测。"
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "get_weather": {
        "label": "天气查询",
        "description": (
            "查询指定城市或地区的实时气温/降水/风力，并给出未来数小时（默认约 12 小时）"
            "的逐时段预报与出行/穿衣建议。仅用于当地天气实况与短时预报；"
            "不得用此工具回答台风名称、路径或预警（请改用 web_search）。"
            "若返回【定位校验失败】须如实告知用户，禁止编造该城市天气。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市或地区名，例如：杭州、杭州萧山、北京（区县建议带上级市名）",
                },
                "forecast_hours": {
                    "type": "integer",
                    "description": "预报未来多少小时，3-24，默认 12",
                },
            },
            "required": ["city"],
        },
    },
    "web_search": {
        "label": "联网搜索",
        "description": (
            "搜索互联网上的实时信息，适用于台风路径/气象预警、新闻、政策、节假日安排、股价、"
            "公开资料等知识库中没有的内容。台风、预警类问题必须调用本工具（查询应含当年年份与台风名），"
            "不要用于已有内部文档可回答的问题。"
            "若需要某站点结构化数据（电商报价/Reddit评论/域名可否注册/房源列表等），改用 "
            "reefapi_search + reefapi_call。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或完整问句，例如：2026年台风白海豚路径、今日科技新闻",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回条数，1-10，默认 5",
                },
                "days": {
                    "type": "integer",
                    "description": "仅保留近 N 天结果，1-30；台风/新闻类默认 3",
                },
            },
            "required": ["query"],
        },
    },
    "reefapi_search": {
        "label": "ReefAPI 引擎发现",
        "description": (
            "发现 ReefAPI 实时网页数据引擎（电商/社交/新闻/域名/房产/公司情报等 160+）。"
            "需要某网站结构化数据、反爬页面、比价、评论、域名是否可注册时：先本工具，再 reefapi_call。"
            "query 用英文意图关键词更准（如 amazon reviews、reddit comments、domain availability）；"
            "指定 engine 可查看该引擎全部 action 与参数。"
            "内部制度/已入库文档仍用 kb_search；通用网页摘要用 web_search。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "英文或中文意图关键词，空则返回匹配摘要列表",
                },
                "engine": {
                    "type": "string",
                    "description": "已知引擎名（如 amazon、reddit）时填写，返回 actions 与参数说明",
                },
            },
            "required": [],
        },
    },
    "reefapi_call": {
        "label": "ReefAPI 拉数",
        "description": (
            "调用 ReefAPI 某引擎 action，返回结构化 JSON（ok/data/meta/error）。"
            "必须先 reefapi_search 确认 engine/action/参数；失败不计费。"
            "仅用于外部站点实时数据，不替代知识库检索。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "engine": {
                    "type": "string",
                    "description": "引擎名，如 amazon、reddit、zillow",
                },
                "action": {
                    "type": "string",
                    "description": "动作名，如 offers、search、search_comments",
                },
                "params": {
                    "type": "object",
                    "description": "动作参数对象，字段以 reefapi_search(engine=...) 为准",
                },
            },
            "required": ["engine", "action"],
        },
    },
    "kb_search": {
        "label": "知识库检索",
        "description": (
            "检索企业内部知识库。调查、分析、多步推理类问题必须先调用此工具。"
            "每次检索应使用不同或更精确的 query。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索问句或关键词",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回条数，1-10，默认 5",
                },
            },
            "required": ["query"],
        },
    },
    "show_relationship_graph": {
        "label": "关系图展示",
        "description": (
            "查询并生成人物/组织关系图，在对话中可视化展示。"
            "当用户询问上下级、汇报关系、工作关系、组织关系图、谁和谁有关时必调用。"
            "可展示人物画像摘要（职位、部门）。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户原问题或关系查询描述",
                },
                "center_name": {
                    "type": "string",
                    "description": "关系图中心人物或实体名称，如：张三",
                },
                "max_hops": {
                    "type": "integer",
                    "description": "关系扩展跳数 1-3，默认 2",
                },
            },
            "required": ["query"],
        },
    },
    "list_kb_sources": {
        "label": "知识库文档列表",
        "description": (
            "列出已入库文档名称与块数量。用户问「库里有什么」「有哪些文档/课程资料」"
            "或不确定查哪个主题时先调用，再针对性 kb_search。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回条数，1-50，默认 30",
                },
            },
            "required": [],
        },
    },
    "format_structured_output": {
        "label": "结构化排版",
        "description": (
            "将已有要点按指定模板整理为卖点清单、私聊话术、短视频脚本、FAQ 等。"
            "在 kb_search 收集完事实后，需要输出固定格式时调用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "待整理的要点或草稿正文",
                },
                "schema_id": {
                    "type": "string",
                    "description": "模板：selling_points | parent_dm_script | short_video_script | compare_table | faq_bullets | checklist",
                },
            },
            "required": ["content", "schema_id"],
        },
    },
}

DEFAULT_CONFIG: dict[str, Any] = {
    "chat_tools_enabled": True,
    "tools": {
        tid: {"enabled": True, "label": meta["label"]}
        for tid, meta in TOOL_DEFINITIONS.items()
    },
}


def load_tools_config() -> dict[str, Any]:
    return load_json_config(DEFAULT_CONFIG)


def save_tools_config(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_tools_config()
    if "chat_tools_enabled" in patch:
        current["chat_tools_enabled"] = bool(patch["chat_tools_enabled"])
    if "tools" in patch and isinstance(patch["tools"], dict):
        for tid, row in patch["tools"].items():
            if tid in current["tools"] and isinstance(row, dict):
                current["tools"][tid].update(row)
    save_json_config(current)
    return current


def enabled_tool_ids(cfg: dict[str, Any] | None = None) -> set[str]:
    c = cfg or load_tools_config()
    if not bool(c.get("chat_tools_enabled", True)):
        return set()
    out: set[str] = set()
    for tid, row in (c.get("tools") or {}).items():
        if tid in TOOL_DEFINITIONS and isinstance(row, dict) and row.get("enabled", True):
            out.add(tid)
    return out


def public_tools_config(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    c = cfg or load_tools_config()
    tools = []
    for tid, meta in TOOL_DEFINITIONS.items():
        row = (c.get("tools") or {}).get(tid) or {}
        tools.append(
            {
                "id": tid,
                "label": row.get("label") or meta.get("label") or tid,
                "description": meta.get("description") or "",
                "enabled": bool(row.get("enabled", True)),
            }
        )
    return {
        "chat_tools_enabled": bool(c.get("chat_tools_enabled", True)),
        "tools": tools,
    }


def execute_tool(tool_id: str, arguments: dict[str, Any]) -> str:
    if tool_id not in TOOL_DEFINITIONS:
        return f"工具未注册：{tool_id}"
    return run_builtin(tool_id, arguments)
