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


def test_dedupe_citation_metas_same_file():
    from agent.context_format import build_source_citations, dedupe_citation_metas

    metas = [
        {"source": "1-9.txt", "parent_id": "p1", "rerank_score": 0.9},
        {"source": "1-9.txt", "parent_id": "p2", "rerank_score": 0.5},
        {"source": "1-3.txt", "parent_id": "p3", "rerank_score": 0.8},
    ]
    deduped = dedupe_citation_metas(metas)
    assert len(deduped) == 2
    assert deduped[0]["parent_id"] == "p1"
    sources, refs = build_source_citations(metas)
    assert len(sources) == 2
    assert len(refs) == 2
    assert all(r["source"] in ("1-9.txt", "1-3.txt") for r in refs)
