"""Tests for the archetype library: definitions, expansion, mapping (issue #26)."""

import pytest

from app.services.archetype_library import (
    ARCHETYPE_DEFINITIONS,
    archetype_to_activity_config,
    expand_archetypes,
    load_archetype_map,
    save_archetype_map,
)

_REQUIRED_KEYS = {
    "name",
    "population_pct",
    "decision_trigger",
    "activity_level",
    "sentiment_bias",
    "influence_weight",
    "persona_template",
    "interests",
    "age_range",
    "karma_range",
    "follower_range",
}


# --- Definitions integrity ---------------------------------------------------

def test_definitions_have_required_keys():
    assert ARCHETYPE_DEFINITIONS, "archetype library should not be empty"
    for key, defn in ARCHETYPE_DEFINITIONS.items():
        missing = _REQUIRED_KEYS - defn.keys()
        assert not missing, f"{key} missing keys: {missing}"


def test_definition_ranges_are_ordered_pairs():
    for key, defn in ARCHETYPE_DEFINITIONS.items():
        for range_key in ("age_range", "karma_range", "follower_range"):
            lo, hi = defn[range_key]
            assert lo <= hi, f"{key}.{range_key} is inverted"


def test_population_percentages_are_plausible():
    total = sum(d["population_pct"] for d in ARCHETYPE_DEFINITIONS.values())
    # Should roughly partition the population (allow rounding slack).
    assert 0.8 <= total <= 1.2


# --- expand_archetypes -------------------------------------------------------

def test_expand_archetypes_produces_exact_count():
    profiles, archetype_map = expand_archetypes(50, product_name="NoShowGuard")
    assert len(profiles) == 50
    assert len(archetype_map) == 50


def test_expand_archetypes_assigns_unique_sequential_ids():
    profiles, archetype_map = expand_archetypes(25)
    ids = [p.user_id for p in profiles]
    assert ids == list(range(25))
    assert [m["agent_id"] for m in archetype_map] == list(range(25))


def test_expand_archetypes_maps_known_archetypes():
    _, archetype_map = expand_archetypes(30)
    for entry in archetype_map:
        assert entry["archetype"] in ARCHETYPE_DEFINITIONS


def test_expand_archetypes_injects_seed_product_context():
    seed = {"competitors": [{"name": "Calendly"}], "features": [{"name": "SMS reminders"}]}
    profiles, _ = expand_archetypes(5, product_name="NoShowGuard", seed_data=seed)
    assert any("Calendly" in p.persona for p in profiles)


@pytest.mark.parametrize("total", [3, 7, 19, 25, 50, 137])
def test_expand_honors_exact_count(total):
    # Regression: small/odd populations must produce exactly `total` agents
    # (no overshoot, no negative intermediate counts).
    profiles, archetype_map = expand_archetypes(total)
    assert len(profiles) == total
    assert len(archetype_map) == total


def test_distribute_population_sums_to_total():
    from app.services.archetype_library import _distribute_population, ARCHETYPE_DEFINITIONS
    keys = list(ARCHETYPE_DEFINITIONS.keys())
    for total in (0, 1, 3, 19, 50, 200):
        counts = _distribute_population(total, keys)
        assert sum(counts.values()) == total
        assert all(c >= 0 for c in counts.values())


# --- activity config + map round-trip ----------------------------------------

def test_archetype_to_activity_config_known_key():
    key = next(iter(ARCHETYPE_DEFINITIONS))
    config = archetype_to_activity_config(key, agent_id=7)
    assert config["agent_id"] == 7
    assert config["entity_type"] == key
    assert "activity_level" in config and "influence_weight" in config


def test_archetype_to_activity_config_unknown_key_returns_empty():
    assert archetype_to_activity_config("not_a_real_archetype", agent_id=1) == {}


def test_save_and_load_archetype_map_round_trip(tmp_path):
    sim_dir = tmp_path / "sim"
    sim_dir.mkdir()
    mapping = [{"agent_id": 0, "archetype": "early_adopter"}]
    save_archetype_map(str(sim_dir), mapping)
    assert load_archetype_map(str(sim_dir)) == mapping


def test_load_archetype_map_missing_returns_empty(tmp_path):
    assert load_archetype_map(str(tmp_path)) == []
