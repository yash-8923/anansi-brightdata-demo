"""Tests for _AdaptiveDomainThrottle."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from anansi.spider.crawler import _AdaptiveDomainThrottle


@pytest.fixture
def throttle() -> _AdaptiveDomainThrottle:
    return _AdaptiveDomainThrottle(base_gap=1.0, enabled=True)


async def test_429_doubles_gap_and_sets_circuit_breaker(throttle: _AdaptiveDomainThrottle) -> None:
    url = "https://example.com/page"
    initial_gap = throttle._gaps["example.com"]

    with patch("time.monotonic", return_value=1000.0):
        await throttle.record_result(url, 429)

    assert throttle._gaps["example.com"] == initial_gap * 2
    assert throttle._cb_until["example.com"] > 1000.0


async def test_429_caps_gap_at_max(throttle: _AdaptiveDomainThrottle) -> None:
    throttle._gaps["example.com"] = 40.0
    url = "https://example.com/page"
    await throttle.record_result(url, 429)
    assert throttle._gaps["example.com"] == throttle._MAX_GAP


async def test_5xx_high_error_rate_expands_gap(throttle: _AdaptiveDomainThrottle) -> None:
    url = "https://example.com/page"
    # Fill window with 80% server errors (above 30% threshold)
    for _ in range(16):
        await throttle.record_result(url, 500)
    for _ in range(4):
        await throttle.record_result(url, 200)

    gap_before = throttle._gaps["example.com"]
    # Trigger expansion with another 5xx
    await throttle.record_result(url, 500)
    assert throttle._gaps["example.com"] > gap_before


async def test_clean_window_shrinks_gap(throttle: _AdaptiveDomainThrottle) -> None:
    url = "https://example.com/page"
    throttle._gaps["example.com"] = 5.0

    # Fill window with successes
    for _ in range(20):
        await throttle.record_result(url, 200)

    assert throttle._gaps["example.com"] < 5.0


async def test_disabled_throttle_does_nothing(monkeypatch) -> None:
    throttle = _AdaptiveDomainThrottle(base_gap=1.0, enabled=False)
    url = "https://example.com/page"
    await throttle.record_result(url, 429)
    assert throttle._gaps["example.com"] == 1.0  # unchanged


async def test_403_does_not_trigger_circuit_breaker(throttle: _AdaptiveDomainThrottle) -> None:
    url = "https://example.com/page"
    # Fill window entirely with 403s
    for _ in range(20):
        await throttle.record_result(url, 403)

    # 403 should NOT cause gap expansion (it's not in the window)
    assert throttle._gaps["example.com"] == 1.0
    # circuit breaker should not be set
    assert throttle._cb_until.get("example.com", 0.0) == 0.0
