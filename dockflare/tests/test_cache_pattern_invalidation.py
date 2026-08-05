import logging

from app.core import cache as cache_module
from flask import Flask
from flask_caching import Cache


def make_simple_cache():
    app = Flask(__name__)
    simple_cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300})
    simple_cache.init_app(app)
    return simple_cache


def test_delete_keys_by_pattern_removes_matching_simple_cache_keys(monkeypatch):
    simple_cache = make_simple_cache()
    simple_cache.set("dns_records:zone-a:tunnel-1", "a")
    simple_cache.set("dns_records:zone-a:tunnel-2", "b")
    simple_cache.set("dns_records:zone-b:tunnel-1", "c")
    simple_cache.set("zone_details:zone-a", "keep")

    monkeypatch.setattr(cache_module, "cache", simple_cache)

    cache_module._delete_keys_by_pattern("dns_records:zone-a:*")

    assert simple_cache.get("dns_records:zone-a:tunnel-1") is None
    assert simple_cache.get("dns_records:zone-a:tunnel-2") is None
    assert simple_cache.get("dns_records:zone-b:tunnel-1") == "c"
    assert simple_cache.get("zone_details:zone-a") == "keep"


def test_simple_cache_pattern_invalidation_does_not_emit_redis_warning(monkeypatch, caplog):
    simple_cache = make_simple_cache()
    simple_cache.set("dns_records:zone-a:tunnel-1", "a")
    monkeypatch.setattr(cache_module, "cache", simple_cache)

    with caplog.at_level(logging.WARNING):
        cache_module._delete_keys_by_pattern("dns_records:*")

    assert "Pattern-based cache invalidation is only supported with RedisCache" not in caplog.text
    assert simple_cache.get("dns_records:zone-a:tunnel-1") is None
