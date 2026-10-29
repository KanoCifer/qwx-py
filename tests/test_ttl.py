"""TTL 策略与单次覆盖。"""

from __future__ import annotations

from datetime import timedelta

from qwx.ttl import Endpoint, TTLMap, TTLPolicy, TTLPolicyFunc, current_ttl_override, override_ttl


def test_endpoint_is_a_string() -> None:
    endpoint = Endpoint("weather/v1/current")
    assert endpoint == "weather/v1/current"
    assert isinstance(endpoint, str)


def test_ttl_map_uses_fallback_for_unknown_endpoint() -> None:
    policy = TTLMap({Endpoint("a/b"): timedelta(seconds=5)})
    assert policy.ttl(Endpoint("a/b"), timedelta(minutes=1)) == timedelta(seconds=5)
    assert policy.ttl(Endpoint("c/d"), timedelta(minutes=1)) == timedelta(minutes=1)


def test_ttl_map_zero_means_no_cache() -> None:
    policy = TTLMap({Endpoint("a/b"): timedelta(0)})
    assert policy.ttl(Endpoint("a/b"), timedelta(minutes=1)) == timedelta(0)


def test_ttl_policy_func() -> None:
    policy = TTLPolicyFunc(lambda endpoint, fallback: timedelta(seconds=1))
    assert policy.ttl(Endpoint("a/b"), timedelta(minutes=1)) == timedelta(seconds=1)
    assert isinstance(policy, TTLPolicy)


def test_override_is_scoped_to_the_block() -> None:
    assert current_ttl_override() is None
    with override_ttl(timedelta(seconds=30)):
        assert current_ttl_override() == timedelta(seconds=30)
    assert current_ttl_override() is None


def test_override_restores_the_previous_value() -> None:
    with override_ttl(timedelta(seconds=30)):
        with override_ttl(timedelta(seconds=60)):
            assert current_ttl_override() == timedelta(seconds=60)
        assert current_ttl_override() == timedelta(seconds=30)
