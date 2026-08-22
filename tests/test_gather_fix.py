"""Tests for asyncio.gather(return_exceptions=True) fix in AdaptiveParser."""

from __future__ import annotations

from pathlib import Path

import pytest

from anansi.parser.adaptive import AdaptiveParser


_SIMPLE_HTML = """
<html><body>
  <h1 class="title">Hello World</h1>
  <span class="price">$9.99</span>
</body></html>
"""


async def test_one_field_fails_others_still_returned(tmp_path: Path) -> None:
    """A single field that raises internally must not kill the whole extract() call."""
    parser = AdaptiveParser(db_path=tmp_path / "gather_a.db")

    original = parser._extract_field

    async def patched(soup, field_name, cfg, url_pattern):
        if field_name == "bad_field":
            raise RuntimeError("simulated extraction failure")
        return await original(soup, field_name, cfg, url_pattern)

    parser._extract_field = patched

    result = await parser.extract(
        _SIMPLE_HTML,
        {"title": ".title", "bad_field": ".title", "price": ".price"},
        url="https://example.com/product/1",
        use_structured=False,  # skip structured to avoid extra DB calls
    )

    assert result["title"] == "Hello World"
    assert result["price"] == "$9.99"
    assert result["bad_field"] is None  # failed field returns None, no exception


async def test_all_fields_fail_returns_all_none(tmp_path: Path) -> None:
    parser = AdaptiveParser(db_path=tmp_path / "gather_b.db")

    async def always_raise(soup, field_name, cfg, url_pattern):
        raise ValueError("boom")

    parser._extract_field = always_raise

    result = await parser.extract(
        _SIMPLE_HTML,
        {"a": ".x", "b": ".y"},
        url="https://example.com/page",
        use_structured=False,
    )

    assert result == {"a": None, "b": None}


async def test_all_fields_succeed_unchanged(tmp_path: Path) -> None:
    parser = AdaptiveParser(db_path=tmp_path / "gather_c.db")
    result = await parser.extract(
        _SIMPLE_HTML,
        {"title": ".title", "price": ".price"},
        url="https://example.com/product/2",
        use_structured=False,
    )
    assert result["title"] == "Hello World"
    assert result["price"] == "$9.99"
