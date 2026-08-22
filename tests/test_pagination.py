"""Tests for smart pagination detection."""

from __future__ import annotations

import pytest

from anansi.parser.pagination import detect_next_page_url

BASE = "https://example.com/blog"


def test_link_rel_next() -> None:
    html = """
    <html>
    <head><link rel="next" href="https://example.com/blog?page=2"></head>
    <body><p>content</p></body>
    </html>
    """
    assert detect_next_page_url(html, BASE) == "https://example.com/blog?page=2"


def test_anchor_rel_next() -> None:
    html = '<html><body><a rel="next" href="/blog?page=3">Next</a></body></html>'
    result = detect_next_page_url(html, BASE)
    assert result == "https://example.com/blog?page=3"


def test_anchor_text_next() -> None:
    html = '<html><body><a href="/page/2">Next</a></body></html>'
    result = detect_next_page_url(html, BASE)
    assert result == "https://example.com/page/2"


def test_anchor_text_next_with_arrow() -> None:
    html = '<html><body><a href="/page/5">»</a></body></html>'
    result = detect_next_page_url(html, BASE)
    assert result == "https://example.com/page/5"


def test_anchor_text_next_page() -> None:
    html = '<html><body><a href="/articles?p=2">Next Page</a></body></html>'
    result = detect_next_page_url(html, BASE)
    assert result == "https://example.com/articles?p=2"


def test_anchor_class_next() -> None:
    html = '<html><body><a class="pagination-next" href="/blog?page=4">›</a></body></html>'
    result = detect_next_page_url(html, BASE)
    assert result == "https://example.com/blog?page=4"


def test_anchor_id_next() -> None:
    html = '<html><body><a id="btn-next" href="/blog/page/6">Forward</a></body></html>'
    result = detect_next_page_url(html, BASE)
    assert result == "https://example.com/blog/page/6"


def test_query_string_page_increment() -> None:
    current = "https://example.com/search?q=python&page=2"
    html = """
    <html><body>
      <a href="/search?q=python&page=1">1</a>
      <span>2</span>
      <a href="/search?q=python&page=3">3</a>
    </body></html>
    """
    result = detect_next_page_url(html, current)
    assert result is not None
    assert "page=3" in result


def test_no_next_page_returns_none() -> None:
    html = '<html><body><p>Last page — no next link here.</p></body></html>'
    assert detect_next_page_url(html, BASE) is None


def test_never_returns_base_url() -> None:
    # Self-referencing link should not be returned
    html = f'<html><body><a rel="next" href="{BASE}">self</a></body></html>'
    assert detect_next_page_url(html, BASE) is None


def test_link_rel_next_takes_priority_over_text() -> None:
    html = """
    <html>
    <head><link rel="next" href="https://example.com/canonical-next"></head>
    <body><a href="/other-next">Next</a></body>
    </html>
    """
    result = detect_next_page_url(html, BASE)
    assert result == "https://example.com/canonical-next"


def test_relative_href_resolved_to_absolute() -> None:
    html = '<html><body><a href="/blog?page=2">Next</a></body></html>'
    result = detect_next_page_url(html, BASE)
    assert result is not None
    assert result.startswith("https://")
