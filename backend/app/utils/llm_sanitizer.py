"""
Shared output guardrails for LLM / agent responses.

Reasoning models (MiniMax, GLM, DeepSeek, Qwen, etc.) and JSON-mode endpoints
routinely wrap their answer in ``<think>`` reasoning blocks or markdown code
fences, and sometimes emit slightly malformed or truncated JSON. Routing every
agent output through this single layer keeps that provider-specific noise out of
parsed content — which previously surfaced as 500s (see issue #17 / commit
985f789).

Everything here is pure (no network, no model state) so it is cheap to call and
trivial to unit-test.
"""

import json
import re
from typing import Any, Iterable, Optional

# Tags emitted by reasoning models that must never reach parsed content.
_REASONING_TAGS = ("think", "thinking", "reasoning", "reflection", "scratchpad")
_TAGS_ALT = "|".join(_REASONING_TAGS)

# A complete <tag> ... </tag> reasoning block.
_REASONING_BLOCK_RE = re.compile(rf"<({_TAGS_ALT})>[\s\S]*?</\1>", re.IGNORECASE)
# A stray closing tag with no matching opener -> drop everything up to it.
_LEADING_CLOSE_RE = re.compile(rf"^[\s\S]*?</({_TAGS_ALT})>", re.IGNORECASE)
# A stray opening tag with no matching closer (truncated mid-thought).
_TRAILING_OPEN_RE = re.compile(rf"<({_TAGS_ALT})>[\s\S]*$", re.IGNORECASE)

# A fenced ```lang ... ``` code block; group 1 is the inner content.
_FENCE_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n?([\s\S]*?)```")
# A bare (unclosed) fence marker.
_FENCE_MARKER_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n?")


def strip_reasoning(text: str) -> str:
    """Remove reasoning-model thinking blocks, including malformed/truncated ones."""
    if not text:
        return text or ""
    cleaned = _REASONING_BLOCK_RE.sub("", text)
    # Closing tag with no opener: the real answer follows it.
    cleaned = _LEADING_CLOSE_RE.sub("", cleaned)
    # Opening tag with no closer: the answer (if any) precedes it.
    cleaned = _TRAILING_OPEN_RE.sub("", cleaned)
    return cleaned.strip()


def strip_code_fences(text: str) -> str:
    """Return the contents of a markdown code fence, or the de-fenced text."""
    if not text:
        return text or ""
    match = _FENCE_BLOCK_RE.search(text)
    if match:
        return match.group(1).strip()
    # Unclosed fence (e.g. truncated output): just drop the opening marker.
    return _FENCE_MARKER_RE.sub("", text).strip()


def sanitize_content(text: str) -> str:
    """Canonical cleanup for free-text agent output: strip reasoning blocks.

    Code fences are intentionally left alone here — in a free-text answer they may
    be a legitimate code sample. JSON parsing handles fences separately.
    """
    return strip_reasoning(text)


def extract_json_block(text: str) -> Optional[str]:
    """Return the first balanced ``{...}`` / ``[...]`` block, scanning past prose.

    If an opener is found but never balanced (truncated output), returns the
    substring from the opener to the end so :func:`repair_json` can close it.
    """
    if not text:
        return None

    start = -1
    opener = closer = ""
    for i, ch in enumerate(text):
        if ch == "{" or ch == "[":
            start = i
            opener = ch
            closer = "}" if ch == "{" else "]"
            break
    if start == -1:
        return None

    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    # Never balanced -> hand the truncated remainder to the repair pass.
    return text[start:]


def close_truncated_json(text: str) -> str:
    """Best-effort close of JSON cut off by a token limit.

    Scans the text tracking string and bracket state (honouring escapes) so a
    trailing number or key isn't mistaken for an open string, then closes any
    dangling string and unbalanced ``{``/``[`` in LIFO order.
    """
    if not text:
        return text or ""
    s = text.rstrip()
    if not s:
        return s

    stack = []
    in_str = False
    escaped = False
    for ch in s:
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack:
                stack.pop()

    if in_str:
        # Terminated mid-string: close the string literal first.
        s += '"'
    else:
        # Drop a dangling separator left by the truncation (e.g. trailing comma).
        s = re.sub(r"[,\s]+$", "", s)
    for closer in reversed(stack):
        s += closer
    return s


def _collapse_string_newlines(text: str) -> str:
    """Collapse raw newlines inside JSON string literals to single spaces."""

    def _fix(match: "re.Match[str]") -> str:
        value = match.group(0).replace("\n", " ").replace("\r", " ")
        return re.sub(r"\s+", " ", value)

    return re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', _fix, text)


def _strip_control_chars(text: str) -> str:
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)
    return re.sub(r"\s+", " ", text)


def repair_json(text: str) -> Optional[Any]:
    """Attempt to parse malformed JSON via progressively aggressive repairs.

    Returns the parsed object, or ``None`` if every attempt fails.
    """
    if not text:
        return None

    candidate = extract_json_block(text)
    if candidate is None:
        candidate = text.strip()

    closed = close_truncated_json(candidate)
    attempts = (
        candidate,
        closed,
        _collapse_string_newlines(closed),
        _strip_control_chars(_collapse_string_newlines(closed)),
    )
    for attempt in attempts:
        try:
            return json.loads(attempt)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def parse_json(text: str, required_keys: Optional[Iterable[str]] = None) -> Any:
    """Sanitize and parse an LLM response into JSON, repairing if needed.

    Strips reasoning blocks and code fences, parses, and falls back to
    :func:`repair_json` for malformed/truncated output. Raises ``ValueError``
    (never a bare ``JSONDecodeError``) when the response is genuinely unusable,
    so callers can handle a single, predictable failure mode instead of leaking
    500s.

    Args:
        text: Raw model output.
        required_keys: If given, the parsed object must be a dict containing
            every key — otherwise ``ValueError`` is raised.
    """
    if text is None:
        raise ValueError("Cannot parse JSON from an empty LLM response")

    cleaned = strip_code_fences(strip_reasoning(text))

    data: Optional[Any]
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        data = repair_json(cleaned)

    if data is None:
        snippet = (cleaned or text).strip()[:200]
        raise ValueError(f"LLM returned unparseable JSON: {snippet!r}")

    if required_keys:
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected a JSON object with keys {list(required_keys)}, "
                f"got {type(data).__name__}"
            )
        missing = [key for key in required_keys if key not in data]
        if missing:
            raise ValueError(f"LLM JSON is missing required keys: {missing}")

    return data
