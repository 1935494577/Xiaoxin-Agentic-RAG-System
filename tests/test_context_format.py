from agent.context_format import format_context_with_meta, format_source_citation, source_ref_dict


def test_format_context_with_meta_includes_tags():
    meta = {
        "source": "1-3.txt",
        "department": "技术",
        "permission_label": "1",
        "text": "示例正文",
    }
    out = format_context_with_meta(meta)
    assert "[来源=1-3.txt | 部门=技术 | 标签=1]" in out
    assert "示例正文" in out


def test_format_source_citation_includes_tags():
    meta = {
        "source": "1-3.txt",
        "parent_id": "p_abc",
        "department": "技术",
        "permission_label": "1",
    }
    out = format_source_citation(meta)
    assert out == "1-3.txt#p_abc (部门=技术, 标签=1)"


def test_source_ref_dict():
    meta = {"source": "a.txt", "parent_id": "p1", "department": "d", "permission_label": "public"}
    assert source_ref_dict(meta) == {
        "source": "a.txt",
        "parent_id": "p1",
        "department": "d",
        "permission_label": "public",
    }
