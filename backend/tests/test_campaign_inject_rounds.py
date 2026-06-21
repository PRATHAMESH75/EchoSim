"""Tests for configurable event-injection rounds (issue #3).

Covers the pure validator, CampaignState round-tripping, and create_campaign
wiring (defaults preserve the 7/14 cadence; custom rounds are honoured; invalid
rounds raise before any simulation is provisioned).
"""

import types
from unittest.mock import MagicMock

import pytest

from app.services.campaign_manager import (
    CampaignManager,
    CampaignState,
    MAX_INJECT_ROUND,
    SCENARIO_B_INJECT_ROUND,
    SCENARIO_C_INJECT_ROUND,
    validate_inject_round,
)


# --- validate_inject_round ---------------------------------------------------

def test_validate_inject_round_accepts_valid_int():
    assert validate_inject_round(5) == 5


def test_validate_inject_round_coerces_numeric_string():
    assert validate_inject_round("12") == 12


@pytest.mark.parametrize("bad", [0, -1, MAX_INJECT_ROUND + 1])
def test_validate_inject_round_rejects_out_of_range(bad):
    with pytest.raises(ValueError):
        validate_inject_round(bad)


@pytest.mark.parametrize("bad", ["abc", None, [1]])
def test_validate_inject_round_rejects_non_integer(bad):
    with pytest.raises(ValueError):
        validate_inject_round(bad)


# --- CampaignState -----------------------------------------------------------

def _state(**overrides):
    base = dict(campaign_id="c1", project_id="p1", graph_id="g1", seed_data={})
    base.update(overrides)
    return CampaignState(**base)


def test_state_defaults_preserve_configured_cadence():
    s = _state()
    assert s.scenario_b_inject_round == SCENARIO_B_INJECT_ROUND
    assert s.scenario_c_inject_round == SCENARIO_C_INJECT_ROUND
    d = s.to_dict()
    assert d["scenario_b_inject_round"] == SCENARIO_B_INJECT_ROUND
    assert d["scenario_c_inject_round"] == SCENARIO_C_INJECT_ROUND


def test_state_to_dict_emits_custom_rounds():
    s = _state(scenario_b_inject_round=3, scenario_c_inject_round=9)
    d = s.to_dict()
    assert d["scenario_b_inject_round"] == 3
    assert d["scenario_c_inject_round"] == 9


# --- CampaignManager.create_campaign -----------------------------------------

def _manager():
    """Bare manager with provisioning + persistence stubbed out."""
    mgr = CampaignManager.__new__(CampaignManager)
    sim = MagicMock()
    sim.create_simulation.side_effect = [
        types.SimpleNamespace(simulation_id="sim_a"),
        types.SimpleNamespace(simulation_id="sim_b"),
        types.SimpleNamespace(simulation_id="sim_c"),
    ]
    mgr._sim_manager = sim
    mgr._save = MagicMock()
    return mgr


def test_create_campaign_defaults_to_configured_cadence():
    mgr = _manager()
    camp = mgr.create_campaign(project_id="p", graph_id="g", seed_data={})
    assert camp.scenario_b_inject_round == SCENARIO_B_INJECT_ROUND
    assert camp.scenario_c_inject_round == SCENARIO_C_INJECT_ROUND
    mgr._save.assert_called_once()


def test_create_campaign_honours_custom_rounds():
    mgr = _manager()
    camp = mgr.create_campaign(
        project_id="p", graph_id="g", seed_data={},
        scenario_b_inject_round=4, scenario_c_inject_round=11,
    )
    assert camp.scenario_b_inject_round == 4
    assert camp.scenario_c_inject_round == 11
    assert camp.to_dict()["scenario_b_inject_round"] == 4


@pytest.mark.parametrize("kwargs", [
    {"scenario_b_inject_round": 0},
    {"scenario_c_inject_round": -3},
    {"scenario_b_inject_round": "oops"},
    {"scenario_c_inject_round": MAX_INJECT_ROUND + 1},
])
def test_create_campaign_rejects_invalid_rounds_before_provisioning(kwargs):
    mgr = _manager()
    with pytest.raises(ValueError):
        mgr.create_campaign(project_id="p", graph_id="g", seed_data={}, **kwargs)
    # Validation must happen before any simulation is provisioned or persisted.
    mgr._sim_manager.create_simulation.assert_not_called()
    mgr._save.assert_not_called()
