"""Stream-path lightweight verifier (TDD)."""

from unittest.mock import MagicMock, patch

from agent.stream_verifier import run_stream_verifier


def _runtime():
    return {
        "llm_api_key": "sk-test",
        "llm_api_base": "https://example.com/v1",
        "chat_model": "gpt-test",
        "llm_temperature_verifier": 0.0,
        "llm_max_tokens_verifier": 8,
    }


def test_skips_general_mode():
    out = run_stream_verifier(
        answer="hello",
        contexts=["ctx"],
        answer_mode="general",
        enabled=True,
        llm_runtime=_runtime(),
    )
    assert out["verifier_decision"] == "pass"
    assert out["verified"] is True
    assert out["answer"] == "hello"


def test_skips_when_disabled():
    out = run_stream_verifier(
        answer="hello",
        contexts=["ctx"],
        answer_mode="kb",
        enabled=False,
        llm_runtime=_runtime(),
    )
    assert out["verified"] is True
    assert out["verifier_decision"] == "pass"


def test_skips_without_api_key():
    out = run_stream_verifier(
        answer="hello",
        contexts=["ctx"],
        answer_mode="kb",
        enabled=True,
        llm_runtime={"llm_api_key": ""},
    )
    assert out["verified"] is True


@patch("agent.stream_verifier.OpenAI")
def test_pass_on_llm_pass(mock_openai):
    client = MagicMock()
    mock_openai.return_value = client
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="PASS"))]
    )
    out = run_stream_verifier(
        answer="制度要求每周阅读",
        contexts=["每周超脑阅读一次"],
        answer_mode="kb",
        enabled=True,
        llm_runtime=_runtime(),
    )
    assert out["verifier_decision"] == "pass"
    assert out["verified"] is True
    assert out["answer"] == "制度要求每周阅读"


@patch("agent.stream_verifier.OpenAI")
def test_reject_on_llm_reject(mock_openai):
    client = MagicMock()
    mock_openai.return_value = client
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="REJECT"))]
    )
    out = run_stream_verifier(
        answer="编造内容",
        contexts=["无关资料"],
        answer_mode="kb",
        enabled=True,
        llm_runtime=_runtime(),
    )
    assert out["verifier_decision"] == "reject"
    assert out["verified"] is False
    assert "无法根据资料确认" in out["answer"]


@patch("agent.stream_verifier.OpenAI")
def test_retry_treated_as_pass_in_stream(mock_openai):
    client = MagicMock()
    mock_openai.return_value = client
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="RETRY"))]
    )
    out = run_stream_verifier(
        answer="略有不符",
        contexts=["资料"],
        answer_mode="kb",
        enabled=True,
        llm_runtime=_runtime(),
    )
    assert out["verifier_decision"] == "pass"
    assert out["verified"] is True
