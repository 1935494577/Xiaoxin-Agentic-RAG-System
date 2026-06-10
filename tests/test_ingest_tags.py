import importlib.util
import sys
from pathlib import Path

UTILS_PATH = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src" / "chunker" / "utils.py"
spec = importlib.util.spec_from_file_location("chunker_utils_test", UTILS_PATH)
assert spec and spec.loader
utils = importlib.util.module_from_spec(spec)
sys.modules["chunker_utils_test"] = utils
spec.loader.exec_module(utils)

normalize_ingest_tags = utils.normalize_ingest_tags
tags_from_store_value = utils.tags_from_store_value
tags_to_store_value = utils.tags_to_store_value


def test_normalize_ingest_tags_dedupes_and_limits():
    raw = ["培训", "培训", "  产品 ", "", "A" * 40]
    out = normalize_ingest_tags(raw)
    assert out == ["培训", "产品", "A" * 32]


def test_normalize_ingest_tags_from_string():
    assert normalize_ingest_tags("制度，培训,制度") == ["制度", "培训"]


def test_tags_store_roundtrip():
    tags = ["FAQ", "内部"]
    stored = tags_to_store_value(tags)
    assert stored == "FAQ,内部"
    assert tags_from_store_value(stored) == tags
