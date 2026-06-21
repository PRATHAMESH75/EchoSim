"""Tests for per-task model selection and backup-model fallback (issue #15)."""

import pytest

from app.config import Config
from app.utils.llm_client import LLMClient


# --- Config.model_for_task ---------------------------------------------------

def test_model_for_task_uses_override(monkeypatch):
    monkeypatch.setattr(Config, "LLM_MODEL_NAME", "global-model")
    monkeypatch.setattr(
        Config, "LLM_TASK_MODELS", {"report": "report-model", "profile": None}
    )
    assert Config.model_for_task("report") == "report-model"


def test_model_for_task_falls_back_to_global(monkeypatch):
    monkeypatch.setattr(Config, "LLM_MODEL_NAME", "global-model")
    monkeypatch.setattr(Config, "LLM_TASK_MODELS", {"profile": None})
    # Unset task override and unknown task both resolve to the global default.
    assert Config.model_for_task("profile") == "global-model"
    assert Config.model_for_task("does-not-exist") == "global-model"
    assert Config.model_for_task(None) == "global-model"


def test_llm_settings_includes_fallback_when_configured(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "primary-key")
    monkeypatch.setattr(Config, "LLM_BASE_URL", "https://primary/v1")
    monkeypatch.setattr(Config, "LLM_MODEL_NAME", "global-model")
    monkeypatch.setattr(Config, "LLM_TASK_MODELS", {"report": "report-model"})
    monkeypatch.setattr(Config, "LLM_FALLBACK_MODEL", "backup-model")
    monkeypatch.setattr(Config, "LLM_FALLBACK_BASE_URL", "https://backup/v1")
    monkeypatch.setattr(Config, "LLM_FALLBACK_API_KEY", "backup-key")

    settings = Config.llm_settings("report")
    assert settings == {
        "api_key": "primary-key",
        "base_url": "https://primary/v1",
        "model": "report-model",
        "fallback_model": "backup-model",
        "fallback_base_url": "https://backup/v1",
        "fallback_api_key": "backup-key",
    }


def test_llm_settings_fallback_defaults_to_primary_connection(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "primary-key")
    monkeypatch.setattr(Config, "LLM_BASE_URL", "https://primary/v1")
    monkeypatch.setattr(Config, "LLM_MODEL_NAME", "global-model")
    monkeypatch.setattr(Config, "LLM_TASK_MODELS", {})
    monkeypatch.setattr(Config, "LLM_FALLBACK_MODEL", "backup-model")
    monkeypatch.setattr(Config, "LLM_FALLBACK_BASE_URL", "")
    monkeypatch.setattr(Config, "LLM_FALLBACK_API_KEY", "")

    settings = Config.llm_settings("report")
    assert settings["fallback_base_url"] == "https://primary/v1"
    assert settings["fallback_api_key"] == "primary-key"


def test_llm_settings_no_fallback_when_unset(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "primary-key")
    monkeypatch.setattr(Config, "LLM_MODEL_NAME", "global-model")
    monkeypatch.setattr(Config, "LLM_TASK_MODELS", {})
    monkeypatch.setattr(Config, "LLM_FALLBACK_MODEL", "")

    settings = Config.llm_settings("report")
    assert settings["fallback_model"] is None
    assert settings["fallback_base_url"] is None
    assert settings["fallback_api_key"] is None


# --- Fake OpenAI client ------------------------------------------------------

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)
        self.finish_reason = "stop"


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _RecordingClient:
    """Returns canned content (or raises) and records the model it was called with."""

    def __init__(self, content=None, error=None):
        self._content = content
        self._error = error
        self.calls = []

        class _Completions:
            def create(_self, **kwargs):
                self.calls.append(kwargs.get("model"))
                if self._error is not None:
                    raise self._error
                return _FakeCompletion(self._content)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


# --- LLMClient.for_task ------------------------------------------------------

def test_for_task_builds_client_with_task_model(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "primary-key")
    monkeypatch.setattr(Config, "LLM_MODEL_NAME", "global-model")
    monkeypatch.setattr(Config, "LLM_TASK_MODELS", {"report": "report-model"})
    monkeypatch.setattr(Config, "LLM_FALLBACK_MODEL", "")

    client = LLMClient.for_task("report")
    assert client.model == "report-model"
    assert client.fallback_model is None


def test_for_task_override_takes_precedence(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "primary-key")
    monkeypatch.setattr(Config, "LLM_MODEL_NAME", "global-model")
    monkeypatch.setattr(Config, "LLM_TASK_MODELS", {"report": "report-model"})
    monkeypatch.setattr(Config, "LLM_FALLBACK_MODEL", "")

    client = LLMClient.for_task("report", model="forced-model")
    assert client.model == "forced-model"


# --- Fallback behaviour ------------------------------------------------------

def test_chat_falls_back_to_backup_on_primary_failure(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "primary-key")
    client = LLMClient(
        api_key="primary-key",
        model="primary-model",
        fallback_model="backup-model",
    )
    client.client = _RecordingClient(error=RuntimeError("primary down"))
    backup = _RecordingClient(content="from backup")
    client._fallback_client = backup

    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == "from backup"
    assert backup.calls == ["backup-model"]


def test_chat_no_fallback_propagates_error(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "primary-key")
    client = LLMClient(api_key="primary-key", model="primary-model")
    client.client = _RecordingClient(error=RuntimeError("primary down"))

    with pytest.raises(RuntimeError, match="primary down"):
        client.chat([{"role": "user", "content": "hi"}])


def test_chat_uses_primary_when_it_succeeds(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "primary-key")
    client = LLMClient(
        api_key="primary-key",
        model="primary-model",
        fallback_model="backup-model",
    )
    primary = _RecordingClient(content="from primary")
    client.client = primary
    backup = _RecordingClient(content="from backup")
    client._fallback_client = backup

    result = client.chat([{"role": "user", "content": "hi"}])
    assert result == "from primary"
    assert primary.calls == ["primary-model"]
    assert backup.calls == []  # backup never touched


def test_fallback_skipped_when_same_as_primary(monkeypatch):
    monkeypatch.setattr(Config, "LLM_API_KEY", "primary-key")
    client = LLMClient(
        api_key="primary-key",
        model="same-model",
        fallback_model="same-model",
    )
    client.client = _RecordingClient(error=RuntimeError("down"))
    # No distinct backup model -> error should propagate, not loop on itself.
    with pytest.raises(RuntimeError, match="down"):
        client.chat([{"role": "user", "content": "hi"}])
