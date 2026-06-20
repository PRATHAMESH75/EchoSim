"""Tests for the disk-backed LLM response cache (issue #20)."""

import time

from app.utils.llm_cache import LLMResponseCache, hash_key


def _cache(tmp_path, namespace="profile", **kwargs):
    kwargs.setdefault("enabled", True)
    kwargs.setdefault("cache_dir", str(tmp_path))
    return LLMResponseCache(namespace, **kwargs)


def test_set_then_get_round_trips(tmp_path):
    cache = _cache(tmp_path)
    material = {"model": "m", "prompt": "hello"}
    assert cache.get(material) is None  # miss

    value = {"bio": "x", "persona": "y"}
    cache.set(material, value)
    assert cache.get(material) == value


def test_distinct_material_does_not_collide(tmp_path):
    cache = _cache(tmp_path)
    cache.set({"prompt": "a"}, "result-a")
    cache.set({"prompt": "b"}, "result-b")
    assert cache.get({"prompt": "a"}) == "result-a"
    assert cache.get({"prompt": "b"}) == "result-b"


def test_key_is_order_independent(tmp_path):
    cache = _cache(tmp_path)
    cache.set({"a": 1, "b": 2}, "v")
    # Same logical material, different dict ordering -> same cache entry.
    assert cache.get({"b": 2, "a": 1}) == "v"


def test_disabled_cache_is_a_noop(tmp_path):
    cache = _cache(tmp_path, enabled=False)
    cache.set({"prompt": "x"}, "v")
    assert cache.get({"prompt": "x"}) is None


def test_ttl_zero_never_expires(tmp_path):
    cache = _cache(tmp_path, ttl=0)
    material = {"prompt": "x"}
    cache.set(material, "v")
    # Backdate the entry; with ttl=0 it must still be served.
    _backdate(cache, material, seconds_ago=10_000)
    assert cache.get(material) == "v"


def test_ttl_expires_old_entries(tmp_path):
    cache = _cache(tmp_path, ttl=1)
    material = {"prompt": "x"}
    cache.set(material, "v")
    assert cache.get(material) == "v"  # fresh -> hit
    _backdate(cache, material, seconds_ago=10)
    assert cache.get(material) is None  # older than ttl -> miss


def _backdate(cache, material, seconds_ago):
    import json
    path = cache._path(hash_key(material))
    with open(path, "r", encoding="utf-8") as fh:
        entry = json.load(fh)
    entry["stored_at"] = time.time() - seconds_ago
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(entry, fh)


def test_namespaces_are_isolated(tmp_path):
    profile = _cache(tmp_path, namespace="profile")
    config = _cache(tmp_path, namespace="config")
    profile.set({"prompt": "x"}, "profile-value")
    assert config.get({"prompt": "x"}) is None
    config.set({"prompt": "x"}, "config-value")
    assert profile.get({"prompt": "x"}) == "profile-value"
    assert config.get({"prompt": "x"}) == "config-value"


def test_corrupt_entry_is_a_miss(tmp_path):
    cache = _cache(tmp_path)
    material = {"prompt": "x"}
    cache.set(material, "v")
    with open(cache._path(hash_key(material)), "w", encoding="utf-8") as fh:
        fh.write("{ not valid json")
    assert cache.get(material) is None


def test_hash_key_is_stable_and_hex(tmp_path):
    key = hash_key({"a": 1})
    assert key == hash_key({"a": 1})
    assert len(key) == 64 and all(c in "0123456789abcdef" for c in key)
