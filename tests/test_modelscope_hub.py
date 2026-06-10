import importlib.util
import sys
from pathlib import Path

MOD_PATH = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src" / "indexing" / "modelscope_hub.py"
spec = importlib.util.spec_from_file_location("modelscope_hub_test", MOD_PATH)
assert spec and spec.loader
hub = importlib.util.module_from_spec(spec)
sys.modules["modelscope_hub_test"] = hub
spec.loader.exec_module(hub)


def test_ms_escape_segment():
    assert hub._ms_escape_segment("bge-small-zh-v1.5") == "bge-small-zh-v1___5"


def test_pick_weight_dir_prefers_escaped_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(hub, "_cache_root", lambda: tmp_path)
    weights = tmp_path / "BAAI" / "bge-small-zh-v1___5"
    weights.mkdir(parents=True)
    (weights / "config.json").write_text("{}", encoding="utf-8")

    picked = hub._pick_weight_dir("BAAI/bge-small-zh-v1.5")
    assert picked == weights
