from unittest.mock import MagicMock

from agent.tools.runtime.tool_context import (
    compress_web_search_output,
    condense_with_llm,
    prepare_tool_content_for_llm,
    truncate_tool_output_for_llm,
)


def test_short_output_passes_through():
    s = "北京时间：2026年06月13日 15:13:01"
    assert prepare_tool_content_for_llm(s, tool_name="get_beijing_time") == s


def test_web_search_structural_compress():
    raw = (
        "搜索「端午节」结果：\n\n"
        "【摘要】2026年端午节在6月19日。\n\n"
        "1. 标题一\n"
        "   " + "内容" * 120 + "\n"
        "   链接: https://a.com\n\n"
        "2. 标题二\n"
        "   短内容\n"
        "   链接: https://b.com\n\n"
        "3. 标题三\n"
        "   三\n"
        "   链接: https://c.com\n\n"
        "4. 标题四\n"
        "   四\n"
        "   链接: https://d.com\n"
    )
    out = compress_web_search_output(raw)
    assert "【摘要】" in out
    assert "标题一" in out
    assert "标题四" not in out
    assert "另有 1 条" in out
    assert len(out) < len(raw)


def test_prepare_uses_llm_condense_when_long():
    client = MagicMock()
    msg = MagicMock()
    msg.content = "2026年端午节是6月19日（周五）。"
    client.chat.completions.create.return_value.choices = [MagicMock(message=msg)]

    raw = "x" * 1200
    out = prepare_tool_content_for_llm(
        raw,
        tool_name="web_search",
        question="今年端午节什么时候？",
        client=client,
        condense_model="mini",
        condense_enabled=True,
    )
    assert "6月19日" in out
    client.chat.completions.create.assert_called_once()


def test_truncate_only_as_last_resort():
    s = "y" * 5000
    out = truncate_tool_output_for_llm(s, max_chars=2000)
    assert len(out) < 5000
    assert "上下文长度上限" in out
