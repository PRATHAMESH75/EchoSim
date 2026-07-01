"""Tests for issue #29 (A2): event injection must not be reported as
successful when the underlying interview call didn't actually reach agents.

Covers both the manual injection path (inject_scenario_event) and the
auto/staggered injection path (_execute_pending_injections).
"""

from unittest.mock import MagicMock

from app.services import campaign_manager as cm_module
from app.services.campaign_manager import CampaignManager, CampaignState


def _state(**overrides):
    base = dict(
        campaign_id="c1", project_id="p1", graph_id="g1",
        seed_data={"product_name": "Widget"}, sim_id_b="sim_b", sim_id_c="sim_c",
    )
    base.update(overrides)
    return CampaignState(**base)


def _manager(state):
    mgr = CampaignManager.__new__(CampaignManager)
    mgr._save = MagicMock()
    mgr._load = MagicMock(return_value=state)
    return mgr


# --- inject_scenario_event (manual injection) --------------------------------

def test_inject_scenario_event_marks_injected_on_success(monkeypatch):
    state = _state()
    mgr = _manager(state)
    monkeypatch.setattr(
        cm_module.SimulationRunner, "interview_all_agents",
        MagicMock(return_value={"success": True, "interviews_count": 5}),
    )

    result = mgr.inject_scenario_event(campaign_id="c1", scenario="b", custom_prompt="hi")

    assert result["success"] is True
    assert state.scenario_b_injected is True
    mgr._save.assert_called_once()


def test_inject_scenario_event_does_not_mark_injected_on_reported_failure(monkeypatch):
    state = _state()
    mgr = _manager(state)
    monkeypatch.setattr(
        cm_module.SimulationRunner, "interview_all_agents",
        MagicMock(return_value={"success": False, "error": "env not running"}),
    )

    result = mgr.inject_scenario_event(campaign_id="c1", scenario="b", custom_prompt="hi")

    assert result["success"] is False
    assert state.scenario_b_injected is False
    mgr._save.assert_not_called()


# --- _execute_pending_injections (auto/staggered injection) ------------------

def _pending(scenario="b", sim_id="sim_b", round_num=7):
    return [{
        "round": round_num, "sim_id": sim_id, "scenario": scenario,
        "prompt": "p1", "tier": "high", "done": False,
    }]


def test_execute_pending_injections_marks_scenario_injected_on_success(monkeypatch):
    state = _state(pending_injections=_pending())
    mgr = _manager(state)
    monkeypatch.setattr(
        cm_module.SimulationRunner, "interview_all_agents",
        MagicMock(return_value={"success": True, "interviews_count": 5}),
    )

    mgr._execute_pending_injections(campaign=state, sim_id="sim_b", current_round=7)

    assert state.pending_injections[0]["done"] is True
    assert state.scenario_b_injected is True


def test_execute_pending_injections_does_not_mark_injected_when_reported_failure(monkeypatch):
    state = _state(pending_injections=_pending())
    mgr = _manager(state)
    monkeypatch.setattr(
        cm_module.SimulationRunner, "interview_all_agents",
        MagicMock(return_value={"success": False, "error": "env not running"}),
    )

    mgr._execute_pending_injections(campaign=state, sim_id="sim_b", current_round=7)

    assert state.pending_injections[0]["done"] is True
    assert state.scenario_b_injected is False


def test_execute_pending_injections_does_not_mark_injected_on_exception(monkeypatch):
    state = _state(pending_injections=_pending())
    mgr = _manager(state)

    def _raise(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(cm_module.SimulationRunner, "interview_all_agents", _raise)

    mgr._execute_pending_injections(campaign=state, sim_id="sim_b", current_round=7)

    assert state.pending_injections[0]["done"] is True
    assert state.scenario_b_injected is False
