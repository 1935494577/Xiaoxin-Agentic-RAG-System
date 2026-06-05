"""使用操作教程。"""

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
    ui, _, _ = init_app_page(api_base, auth, prof_data, check_model_status=False)

    st.title("使用操作教程")
    fmt = ui.get("supported_upload_label") or "TXT · MD · PDF · DOCX · HTML"

    st.markdown(
        f"""
### 1. 配置大模型（管理员）
打开左侧 **模型接入 → 模型设置**，填写 API 地址与密钥，测试通过后保存。

### 2. 上传文档入库
打开 **程序与配置 → 数据入库**：
- 支持格式：**{fmt}**
- 选择 **归属部门** 与 **可见范围**
- 勾选 **自动脱敏** 后上传文件，点击 **确认入库**

### 3. RAG 对话提问
打开 **RAG 对话**，输入问题或点击推荐问题，助手将基于知识库内容回答。

### 常见问题
- **搜不到文档**：入库与对话使用的「归属部门」需一致（默认技术）。
- **无法回答**：请联系管理员检查模型接入配置。
        """
    )


if __name__ == "__main__":
    main()
