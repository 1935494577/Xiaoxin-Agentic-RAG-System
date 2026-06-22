"""Tests for /chat/transcribe endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def test_transcribe_requires_api_key(client, monkeypatch):
    monkeypatch.setattr("api.speech_transcribe.settings.openai_api_key", "")
    r = client.post(
        "/chat/transcribe",
        files={"file": ("speech.webm", b"fake-audio", "audio/webm")},
    )
    assert r.status_code == 400
    assert "API Key" in r.json()["detail"]


def test_transcribe_success(client, monkeypatch):
    monkeypatch.setattr("api.speech_transcribe.settings.openai_api_key", "test-key")

    def _fake(content: bytes, filename: str, *, language: str = "zh", **_: object) -> str:
        assert content == b"audio-bytes"
        assert filename == "speech.webm"
        assert language == "zh"
        return "超脑阅读要求"

    monkeypatch.setattr("api.main.transcribe_audio_bytes", _fake)
    r = client.post(
        "/chat/transcribe",
        files={"file": ("speech.webm", b"audio-bytes", "audio/webm")},
        params={"language": "zh"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "超脑阅读要求"


def test_transcribe_rejects_empty(client, monkeypatch):
    monkeypatch.setattr("api.speech_transcribe.settings.openai_api_key", "test-key")
    r = client.post(
        "/chat/transcribe",
        files={"file": ("speech.webm", b"", "audio/webm")},
    )
    assert r.status_code == 400
