"""Tests for outbound LLM retry/backoff + uniform error surface (issue #28)."""

import pytest

import app.utils.llm_client as llm_mod
from app.config import Config
from app.utils.llm_client import LLMClient, LLMError, _TRANSIENT_LLM_ERRORS


class _Transient(Exception):
    """Stand-in transient provider error."""


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


class _FlakyClient:
    """Raises ``error`` for the first ``fail_times`` calls, then returns content."""

    def __init__(self, fail_times, error, content="ok"):
        self.fail_times = fail_times
        self.error = error
        self.content = content
        self.attempts = 0

        class _Completions:
            def create(_self, **kwargs):
                self.attempts += 1
                if self.attempts <= self.fail_times:
                    raise self.error
                return _FakeCompletion(self.content)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch):
    # Treat _Transient as retryable and make backoff instant.
    monkeypatch.setattr(llm_mod, "_TRANSIENT_LLM_ERRORS", (_Transient,))
    monkeypatch.setattr(llm_mod.time, "sleep", lambda *_: None)
    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(Config, "LLM_MAX_RETRIES", 3)
    monkeypatch.setattr(Config, "LLM_RETRY_INITIAL_DELAY", 0.0)


def _client(**kwargs):
    return LLMClient(api_key="test-key", model="primary-model", **kwargs)


def test_retries_transient_then_succeeds():
    client = _client()
    flaky = _FlakyClient(fail_times=2, error=_Transient("429"))
    client.client = flaky

    assert client.chat([{"role": "user", "content": "hi"}]) == "ok"
    assert flaky.attempts == 3  # 2 failures + 1 success


def test_exhausted_retries_raise_llm_error():
    client = _client()
    flaky = _FlakyClient(fail_times=99, error=_Transient("still 429"))
    client.client = flaky

    with pytest.raises(LLMError) as exc:
        client.chat([{"role": "user", "content": "hi"}])
    assert flaky.attempts == Config.LLM_MAX_RETRIES + 1  # initial try + retries
    # Uniform, actionable message that surfaces the model and original detail.
    assert "primary-model" in str(exc.value)
    assert "still 429" in str(exc.value)


def test_non_transient_error_is_not_retried():
    client = _client()
    flaky = _FlakyClient(fail_times=99, error=ValueError("bad request"))
    client.client = flaky

    with pytest.raises(LLMError):
        client.chat([{"role": "user", "content": "hi"}])
    assert flaky.attempts == 1  # no retries on non-transient errors


def test_transient_on_primary_then_fallback_succeeds():
    client = _client(fallback_model="backup-model")
    client.client = _FlakyClient(fail_times=99, error=_Transient("primary 429"))
    backup = _FlakyClient(fail_times=0, error=_Transient("unused"), content="from backup")
    client._fallback_client = backup

    assert client.chat([{"role": "user", "content": "hi"}]) == "from backup"
    assert backup.attempts == 1


def test_timeout_error_class_is_transient():
    from openai import APITimeoutError
    # Guards against an SDK change silently dropping timeouts from the retry set.
    assert APITimeoutError in _TRANSIENT_LLM_ERRORS
