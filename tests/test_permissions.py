from security.permissions import filter_by_sources


def test_filter_none_means_no_filter():
    ctx = [{"source": "a.txt", "text": "x"}]
    assert filter_by_sources(ctx, None) == ctx


def test_filter_empty_list_returns_nothing():
    ctx = [{"source": "a.txt", "text": "x"}]
    assert filter_by_sources(ctx, []) == []


def test_filter_subset():
    ctx = [
        {"source": "a.txt", "text": "1"},
        {"source": "b.txt", "text": "2"},
    ]
    out = filter_by_sources(ctx, ["b.txt"])
    assert len(out) == 1 and out[0]["source"] == "b.txt"
