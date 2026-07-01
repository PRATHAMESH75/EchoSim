"""Tests for issue #29 (A1): event injection must actually reach a running
simulation instead of silently failing with "environment is not running or
has closed".

`run_parallel_simulation.py` is a standalone script (not part of the `app`
package), so it's loaded directly from its file path. These tests exercise
`ParallelIPCHandler` in isolation with fake envs — no real OASIS/LLM calls —
to verify:
  1. Registering a platform's env marks the environment "alive" immediately,
     instead of only after the full round loop finishes.
  2. An interview-triggered env.step() and the round loop's own env.step()
     never run concurrently on the same env (they'd otherwise race on OASIS's
     internal state).
"""

import asyncio
import importlib.util
import json
import os

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "run_parallel_simulation", os.path.join(SCRIPTS_DIR, "run_parallel_simulation.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rps():
    return _load_module()


class FakeEnv:
    """Stand-in for an OASIS env: asserts the shared lock is held during
    step(), so a lock-free regression fails loudly instead of racing."""

    def __init__(self, lock):
        self.lock = lock
        self.step_calls = 0

    async def step(self, actions):
        assert self.lock.locked(), "env.step() called without holding the platform lock"
        self.step_calls += 1
        await asyncio.sleep(0)  # yield control, like a real awaited call would


class FakeAgentGraph:
    def get_agent(self, agent_id):
        return f"agent_{agent_id}"


def test_register_twitter_marks_env_alive_immediately(tmp_path, rps):
    handler = rps.ParallelIPCHandler(simulation_dir=str(tmp_path))
    lock = asyncio.Lock()

    handler.register_twitter(env="env", agent_graph="graph", lock=lock)

    assert handler.twitter_env == "env"
    assert handler.twitter_lock is lock
    status_file = os.path.join(str(tmp_path), "env_status.json")
    with open(status_file) as f:
        status = json.load(f)
    assert status["status"] == "alive"
    assert status["twitter_available"] is True


def test_register_reddit_marks_env_alive_immediately(tmp_path, rps):
    handler = rps.ParallelIPCHandler(simulation_dir=str(tmp_path))
    lock = asyncio.Lock()

    handler.register_reddit(env="env", agent_graph="graph", lock=lock)

    assert handler.reddit_env == "env"
    assert handler.reddit_lock is lock
    status_file = os.path.join(str(tmp_path), "env_status.json")
    with open(status_file) as f:
        status = json.load(f)
    assert status["status"] == "alive"
    assert status["reddit_available"] is True


def test_interview_step_and_round_step_never_overlap(tmp_path, rps, monkeypatch):
    """The interview dispatcher and the round loop both call env.step() on the
    same env from independent coroutines. Without the shared lock they could
    interleave into the same OASIS env; with it, FakeEnv.step()'s assertion
    that the lock is held would fail if they ever raced."""

    async def scenario():
        handler = rps.ParallelIPCHandler(simulation_dir=str(tmp_path))
        lock = asyncio.Lock()
        env = FakeEnv(lock)
        graph = FakeAgentGraph()
        handler.register_twitter(env, graph, lock)
        monkeypatch.setattr(
            handler, "_get_interview_result", lambda agent_id, platform: {"agent_id": agent_id}
        )

        async def round_loop_step():
            async with lock:
                await env.step({"round": "action"})

        interview = handler._interview_single_platform(agent_id=1, prompt="hi", platform="twitter")
        round_step = round_loop_step()

        results = await asyncio.gather(interview, round_step)
        assert env.step_calls == 2
        assert "error" not in results[0]

    asyncio.run(scenario())


def test_batch_interview_acquires_lock_before_stepping(tmp_path, rps, monkeypatch):
    async def scenario():
        handler = rps.ParallelIPCHandler(simulation_dir=str(tmp_path))
        lock = asyncio.Lock()
        env = FakeEnv(lock)
        graph = FakeAgentGraph()
        handler.register_twitter(env, graph, lock)
        monkeypatch.setattr(
            handler, "_get_interview_result", lambda agent_id, platform: {"agent_id": agent_id}
        )
        monkeypatch.setattr(handler, "send_response", lambda *a, **k: None)

        async def round_loop_step():
            async with lock:
                await env.step({"round": "action"})

        batch = handler.handle_batch_interview(
            command_id="cmd1",
            interviews=[{"agent_id": 1, "prompt": "hi", "platform": "twitter"}],
        )
        round_step = round_loop_step()

        await asyncio.gather(batch, round_step)
        assert env.step_calls == 2

    asyncio.run(scenario())
