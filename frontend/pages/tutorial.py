"""使用操作教程 — 与当前前后端功能保持一致。"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_FRONT = Path(__file__).resolve().parent.parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))
from _bootstrap import load_streamlit_common  # noqa: E402
from page_init import init_app_page  # noqa: E402

scom = load_streamlit_common(_FRONT)


def main() -> None:
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    api_base = scom.get_api_base()
    auth = scom.get_api_auth_headers()
    prof_data = scom.fetch_model_profiles(api_base)
    ui, _, _ = init_app_page(api_base, auth, prof_data, check_model_status=False, nav_id="tutorial")

    st.title("使用操作教程")
    fmt = ui.get("supported_upload_label") or "TXT · MD · PDF · DOCX · HTML"
    chat_url = "http://127.0.0.1:8502"

    st.markdown(
        f"""
### 服务入口

| 服务 | 地址 | 说明 |
|------|------|------|
| **Jnao Chat** | {chat_url} | 主对话界面（流式 RAG） |
| **管理后台** | 8501 | 入库、配置、模型、提示词等 |
| **API** | 8010 | FastAPI，供前后端调用 |

顶部导航可在 **Jnao Chat** 与管理页之间切换。

---

### 1. 配置大模型
打开 **模型**，填写 OpenAI 兼容 API 地址与密钥，测试通过后保存并设为默认。

### 2. 上传文档入库
打开 **数据入库**（默认首页）：
- 支持格式：**{fmt}**
- 可选 **入库标签**（预设 + 自定义，逗号分隔）
- **已清洗数据** / **未清洗数据** 两种模式；未清洗将走 **工具** 页配置的解析清洗链
- 侧边栏设置 **归属部门** 与可见范围后上传

### 3. 向量库（可选）
**向量库** 页可管理 Milvus Lite / NumPy 等存储实例并切换激活库。

### 4. Jnao Chat 对话
- 默认 **仅知识库检索**；输入框上方可开 **混合专家模式**（知识库优先，未命中时补充通用回答）
- 侧栏选 **部门权限**，与入库部门一致时检索效果更好
- 支持多会话、长期记忆（`session_id` 自动持久化）

### 5. 对话记忆（管理员）
**对话记忆** 页：短期/长期记忆参数、检索阈值、混合专家默认开关、Jnao Chat **推荐问题** 等。

### 6. 提示词（管理员）
**提示词** 页：按 Prompt 工程分层配置 System Prompt（角色人设 → 约束 → 任务 → 输出），可插拔启用/自定义层。

### 7. 工具（管理员）
**工具** 页：入库清洗工具开关、大模型选工具路由。

### 8. 链路 Trace（管理员）
查看 LangSmith / 本地 JSONL 链路说明与 trace 状态。

---

### 常见问题
- **搜不到文档**：对话部门与入库部门需一致（默认「技术」）。
- **Page not found**：数据入库请访问管理后台根路径 `/`，勿用 `/ingest`。
- **模型无回复**：检查 **模型** 页连接状态与 API Key。
        """
    )


if __name__ == "__main__":
    main()
