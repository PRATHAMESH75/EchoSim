"""Tests for the shared LLM output guardrail layer (issue #17)."""

import pytest

from app.utils.llm_sanitizer import (
    close_truncated_json,
    extract_json_block,
    parse_json,
    repair_json,
    sanitize_content,
    strip_code_fences,
    strip_reasoning,
)


# --- strip_reasoning ---------------------------------------------------------

def test_strip_reasoning_removes_wellformed_block():
    text = "<think>let me reason about this</think>The answer is 42."
    assert strip_reasoning(text) == "The answer is 42."


def test_strip_reasoning_handles_truncated_open_tag():
    # Model emitted an opening tag then got cut off mid-thought.
    assert strip_reasoning("<think>still thinking and then cut") == ""


def test_strip_reasoning_handles_orphan_close_tag():
    # Opening tag missing (some providers only stream the closer).
    text = "reasoning noise</think>{\"ok\": true}"
    assert strip_reasoning(text) == '{"ok": true}'


def test_strip_reasoning_supports_tag_variants():
    assert strip_reasoning("<reasoning>x</reasoning>done") == "done"
    assert strip_reasoning("<Thinking>x</Thinking>done") == "done"


# --- strip_code_fences -------------------------------------------------------

def test_strip_code_fences_extracts_inner_json():
    assert strip_code_fences('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_code_fences_handles_unclosed_fence():
    assert strip_code_fences('```json\n{"a": 1}') == '{"a": 1}'


def test_strip_code_fences_noop_without_fence():
    assert strip_code_fences('{"a": 1}') == '{"a": 1}'


# --- extract_json_block ------------------------------------------------------

def test_extract_json_block_skips_surrounding_prose():
    text = 'Sure, here you go: {"name": "x"} hope that helps!'
    assert extract_json_block(text) == '{"name": "x"}'


def test_extract_json_block_handles_array():
    assert extract_json_block("noise [1, 2, 3] tail") == "[1, 2, 3]"


def test_extract_json_block_returns_remainder_when_unbalanced():
    # Truncated object -> hand remainder to the repair pass.
    assert extract_json_block('prefix {"a": 1') == '{"a": 1'


# --- close_truncated_json / repair_json -------------------------------------

def test_repair_json_closes_truncated_object():
    assert repair_json('{"a": 1, "b": 2') == {"a": 1, "b": 2}


def test_repair_json_closes_truncated_nested_structure():
    assert repair_json('{"items": [1, 2, {"k": "v"') == {"items": [1, 2, {"k": "v"}]}


def test_repair_json_collapses_newlines_inside_strings():
    assert repair_json('{"bio": "line one\nline two"}') == {"bio": "line one line two"}


def test_repair_json_returns_none_for_garbage():
    assert repair_json("this is not json at all") is None


def test_close_truncated_json_closes_dangling_string():
    assert close_truncated_json('{"a": "hello') == '{"a": "hello"}'


# --- parse_json (the single validation step) --------------------------------

def test_parse_json_handles_reasoning_then_fenced_json():
    raw = '<think>deciding the shape</think>\n```json\n{"verdict": "build"}\n```'
    assert parse_json(raw) == {"verdict": "build"}


def test_parse_json_repairs_malformed_output_instead_of_raising():
    # Exactly the class of reasoning-model output that used to cause a 500.
    raw = '<think>...</think>{"score": 47, "nps": 12'
    assert parse_json(raw) == {"score": 47, "nps": 12}


def test_parse_json_raises_valueerror_on_unrecoverable_output():
    with pytest.raises(ValueError):
        parse_json("the model refused and wrote a paragraph instead")


def test_parse_json_validates_required_keys():
    with pytest.raises(ValueError, match="missing required keys"):
        parse_json('{"a": 1}', required_keys=["a", "b"])


def test_parse_json_required_keys_rejects_non_object():
    with pytest.raises(ValueError):
        parse_json("[1, 2, 3]", required_keys=["a"])


def test_sanitize_content_is_reasoning_strip():
    assert sanitize_content("<think>x</think>hello") == "hello"


# --- LLMClient integration: malformed output no longer 500s ------------------

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


class _FakeOpenAI:
    """Minimal stand-in for the OpenAI client returning canned content."""

    def __init__(self, content):
        self._content = content

        class _Completions:
            def create(_self, **kwargs):
                return _FakeCompletion(self._content)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


def _make_client(content, monkeypatch):
    from app.config import Config
    from app.utils.llm_client import LLMClient

    monkeypatch.setattr(Config, "LLM_API_KEY", "test-key")
    client = LLMClient(api_key="test-key")
    client.client = _FakeOpenAI(content)
    return client


def test_llmclient_chat_strips_reasoning(monkeypatch):
    client = _make_client("<think>hmm</think>final answer", monkeypatch)
    assert client.chat([{"role": "user", "content": "hi"}]) == "final answer"


def test_llmclient_chat_json_recovers_from_reasoning_model_output(monkeypatch):
    # Reasoning block + fence + truncated brace — previously a 500.
    raw = '<think>deciding</think>\n```json\n{"sentiment": "positive", "nps": 12'
    client = _make_client(raw, monkeypatch)
    assert client.chat_json([{"role": "user", "content": "go"}]) == {
        "sentiment": "positive",
        "nps": 12,
    }


def test_llmclient_chat_json_enforces_required_keys(monkeypatch):
    client = _make_client('{"a": 1}', monkeypatch)
    with pytest.raises(ValueError):
        client.chat_json([{"role": "user", "content": "go"}], required_keys=["a", "b"])
