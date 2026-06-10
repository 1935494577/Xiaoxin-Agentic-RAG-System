import importlib.util
import sys
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src" / "api" / "routing_mode.py"
spec = importlib.util.spec_from_file_location("routing_mode_test", MOD)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules["routing_mode_test"] = mod
spec.loader.exec_module(mod)


def test_apply_hybrid_expert_off():
    base = {"general_fallback_enabled": True, "kb_post_stream_fallback": True}
    out = mod.apply_hybrid_expert_memory(base, False)
    assert out["general_fallback_enabled"] is False
    assert out["kb_post_stream_fallback"] is False


def test_apply_hybrid_expert_on():
    base = {"general_fallback_enabled": False, "kb_post_stream_fallback": False}
    out = mod.apply_hybrid_expert_memory(base, True)
    assert out["general_fallback_enabled"] is True
    assert out["kb_post_stream_fallback"] is True
