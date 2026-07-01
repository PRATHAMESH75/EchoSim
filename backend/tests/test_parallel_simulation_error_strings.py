"""Tests for issue #29 (A3): IPC error strings must be in English.

`run_parallel_simulation.py` previously returned untranslated Chinese error
strings (e.g. "没有成功的采访") from the OASIS/IPC layer, which leaked all the
way to the public `/campaign/<id>/inject` API response. This is a standalone
script (not part of the `app` package), so it's loaded directly from its file
path — no real OASIS/LLM calls involved.
"""

import asyncio
import importlib.util
import os
import re

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
SCRIPT_PATH = os.path.join(SCRIPTS_DIR, "run_parallel_simulation.py")

# Matches any CJK ideograph.
_CJK_RE = re.compile(r"[一-鿿]")


def _load_module():
    spec = importlib.util.spec_from_file_location("run_parallel_simulation", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rps():
    return _load_module()


def test_no_cjk_characters_in_ipc_error_strings():
    """Static regression guard: no `error=...` argument to send_response may
    contain untranslated Chinese text (console-only print() logging is fine)."""
    with open(SCRIPT_PATH, encoding="utf-8") as f:
        source = f.read()

    for match in re.finditer(r"error=(f?[\"'].*?[\"'])", source):
        literal = match.group(1)
        assert not _CJK_RE.search(literal), f"Untranslated CJK text in IPC error string: {literal}"


def test_batch_interview_failure_message_is_english(tmp_path, rps, monkeypatch):
    async def scenario():
        handler = rps.ParallelIPCHandler(simulation_dir=str(tmp_path))
        # No env registered at all -> handle_batch_interview finds nothing to
        # interview and must report the empty-results failure in English.
        captured = {}
        monkeypatch.setattr(
            handler, "send_response",
            lambda command_id, status, result=None, error=None: captured.update(
                {"status": status, "error": error}
            ),
        )

        await handler.handle_batch_interview(
            command_id="cmd1",
            interviews=[{"agent_id": 1, "prompt": "hi", "platform": "twitter"}],
        )

        assert captured["status"] == "failed"
        assert captured["error"] == "No interviews succeeded"
        assert not _CJK_RE.search(captured["error"])

    asyncio.run(scenario())


def test_interview_unavailable_platform_message_is_english(tmp_path, rps):
    async def scenario():
        handler = rps.ParallelIPCHandler(simulation_dir=str(tmp_path))
        # No twitter env registered -> platform unavailable.
        result = await handler._interview_single_platform(agent_id=1, prompt="hi", platform="twitter")
        assert "error" in result
        assert not _CJK_RE.search(result["error"])
        assert result["error"] == "twitter platform is unavailable"

    asyncio.run(scenario())
