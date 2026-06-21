"""Tests for ReportAgent tool-call parsing logic (issue #26).

These exercise the pure parsing/validation helpers without constructing the full
agent (which needs LLM + Zep clients), via ``__new__``.
"""

import pytest

from app.services.report_agent import ReportAgent


@pytest.fixture
def agent():
    # Bare instance: __init__ (LLM/Zep wiring) is skipped; the methods under test
    # only rely on class attributes (VALID_TOOL_NAMES) and other pure methods.
    return ReportAgent.__new__(ReportAgent)


# --- _is_valid_tool_call -----------------------------------------------------

def test_valid_tool_call_accepts_known_name(agent):
    assert agent._is_valid_tool_call({"name": "quick_search", "parameters": {}}) is True


def test_valid_tool_call_rejects_unknown_name(agent):
    assert agent._is_valid_tool_call({"name": "rm_rf_slash"}) is False


def test_valid_tool_call_normalises_tool_and_params_keys(agent):
    data = {"tool": "panorama_search", "params": {"q": "x"}}
    assert agent._is_valid_tool_call(data) is True
    # Keys are normalised in place to name/parameters.
    assert data["name"] == "panorama_search"
    assert data["parameters"] == {"q": "x"}


# --- _parse_tool_calls -------------------------------------------------------

def test_parse_xml_tool_call(agent):
    response = '<tool_call>{"name": "quick_search"}</tool_call>'
    calls = agent._parse_tool_calls(response)
    assert calls == [{"name": "quick_search"}]


def test_parse_xml_tool_call_with_nested_parameters(agent):
    # Guard: a non-empty nested `parameters` object must survive. (This already
    # worked -- the </tool_call> anchor backtracks the old lazy regex to the
    # outer brace -- kept so the balanced-extraction rewrite doesn't regress it.)
    response = '<tool_call>{"name": "insight_forge", "parameters": {"query": "pricing"}}</tool_call>'
    calls = agent._parse_tool_calls(response)
    assert calls == [{"name": "insight_forge", "parameters": {"query": "pricing"}}]


def test_parse_xml_tool_call_with_leading_text_in_tag(agent):
    # Model prefixes the JSON with prose inside the tag. The old
    # `<tool_call>\s*(\{...\})` regex required the object to start right after the
    # tag and dropped this; balanced extraction scans past the prose.
    response = '<tool_call>\nHere you go: {"name": "quick_search", "parameters": {"q": "x"}}</tool_call>'
    calls = agent._parse_tool_calls(response)
    assert calls == [{"name": "quick_search", "parameters": {"q": "x"}}]


def test_parse_xml_tool_call_with_trailing_text_in_tag(agent):
    # A trailing note after the JSON inside the tag. The old regex required the
    # object to end right before </tool_call> and dropped this entirely.
    response = '<tool_call>{"name": "insight_forge", "parameters": {"query": "p"}}\nNote: done</tool_call>'
    calls = agent._parse_tool_calls(response)
    assert calls == [{"name": "insight_forge", "parameters": {"query": "p"}}]


def test_parse_xml_tool_call_with_fenced_json_in_tag(agent):
    # Some models wrap the call in a ```json fence inside the tag.
    response = '<tool_call>```json\n{"name": "quick_search", "parameters": {"q": 1}}\n```</tool_call>'
    calls = agent._parse_tool_calls(response)
    assert calls == [{"name": "quick_search", "parameters": {"q": 1}}]


def test_parse_bare_json_with_nested_parameters(agent):
    response = '{"name": "insight_forge", "parameters": {"query": "pricing"}}'
    calls = agent._parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0]["name"] == "insight_forge"
    assert calls[0]["parameters"] == {"query": "pricing"}


def test_parse_bare_json_invalid_tool_is_ignored(agent):
    assert agent._parse_tool_calls('{"name": "danger", "parameters": {}}') == []


def test_parse_trailing_json_after_reasoning_text(agent):
    response = 'Let me search the graph.\n{"tool": "panorama_search", "params": {"q": 1}}'
    calls = agent._parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0]["name"] == "panorama_search"
    assert calls[0]["parameters"] == {"q": 1}


def test_parse_plain_prose_yields_no_tool_calls(agent):
    assert agent._parse_tool_calls("Here is the final report, no tools needed.") == []
