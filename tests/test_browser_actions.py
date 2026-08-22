"""Tests for browser action error isolation (required vs optional actions)."""

from __future__ import annotations

import logging

import pytest


class _FakePage:
    """Minimal page stub that raises on click but succeeds on other actions."""

    async def click(self, selector: str) -> None:
        raise RuntimeError(f"Element not found: {selector}")

    async def fill(self, selector: str, value: str) -> None:
        pass

    async def evaluate(self, script: str) -> None:
        pass

    async def wait_for_selector(self, selector: str, **kwargs) -> None:
        pass

    async def press(self, selector: str, key: str) -> None:
        pass


async def test_optional_action_failure_does_not_raise(caplog) -> None:
    from anansi.fetchers.browser import BrowserFetcher
    fetcher = BrowserFetcher()
    page = _FakePage()

    actions = [
        {"type": "click", "selector": "#missing", "required": False},
    ]
    with caplog.at_level(logging.WARNING):
        await fetcher._run_actions(page, actions)

    assert any("Optional browser action" in r.message for r in caplog.records)


async def test_required_action_failure_raises_runtime_error() -> None:
    from anansi.fetchers.browser import BrowserFetcher
    fetcher = BrowserFetcher()
    page = _FakePage()

    actions = [
        {"type": "click", "selector": "#missing", "required": True},
    ]
    with pytest.raises(RuntimeError, match="Required browser action #0"):
        await fetcher._run_actions(page, actions)


async def test_no_required_key_defaults_to_required() -> None:
    """Backward-compat: actions without 'required' key should raise on failure."""
    from anansi.fetchers.browser import BrowserFetcher
    fetcher = BrowserFetcher()
    page = _FakePage()

    actions = [{"type": "click", "selector": "#missing"}]
    with pytest.raises(RuntimeError, match="Required browser action #0"):
        await fetcher._run_actions(page, actions)


async def test_optional_fill_succeeds_skips_bad_click(caplog) -> None:
    """Optional bad action is skipped; subsequent actions still run."""
    from anansi.fetchers.browser import BrowserFetcher
    fetcher = BrowserFetcher()
    page = _FakePage()

    ran = []

    async def patched_fill(sel, val):
        ran.append(("fill", sel, val))

    page.fill = patched_fill

    actions = [
        {"type": "click", "selector": "#bad", "required": False},
        {"type": "fill", "selector": "#name", "value": "hello"},
    ]
    with caplog.at_level(logging.WARNING):
        await fetcher._run_actions(page, actions)

    assert ("fill", "#name", "hello") in ran
    assert any("Optional browser action" in r.message for r in caplog.records)
