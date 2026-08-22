"""Tests for _url_to_pattern URL normalization."""

from __future__ import annotations

from anansi.parser.adaptive import _url_to_pattern


def test_numeric_id_collapsed() -> None:
    assert _url_to_pattern("https://example.com/products/12345") == "example.com/products/{id}"


def test_short_numeric_preserved() -> None:
    # 1-2 digit segments should NOT be collapsed (/v1, /category/5)
    assert _url_to_pattern("https://example.com/v1/products") == "example.com/v1/products"
    assert _url_to_pattern("https://example.com/category/5") == "example.com/category/5"


def test_uuid_collapsed() -> None:
    result = _url_to_pattern(
        "https://example.com/items/550e8400-e29b-41d4-a716-446655440000"
    )
    assert result == "example.com/items/{uuid}"


def test_date_triplet_collapsed() -> None:
    result = _url_to_pattern("https://example.com/blog/2024/01/15/my-post")
    assert result == "example.com/blog/{date}/my-post"


def test_year_month_collapsed() -> None:
    result = _url_to_pattern("https://example.com/blog/2024/01/post-slug")
    assert result == "example.com/blog/{year}/{month}/post-slug"


def test_hex_hash_collapsed() -> None:
    result = _url_to_pattern("https://example.com/static/abc123def456abc123def456abc12345")
    assert result == "example.com/static/{hash}"


def test_api_version_preserved() -> None:
    # /v2/ is a single-digit segment, must not be collapsed
    result = _url_to_pattern("https://api.example.com/v2/users/99999")
    assert result == "api.example.com/v2/users/{id}"


def test_query_and_fragment_stripped() -> None:
    result = _url_to_pattern("https://example.com/search?q=test&page=2#results")
    assert "?" not in result
    assert "#" not in result
    assert result == "example.com/search"


def test_invalid_url_returns_original() -> None:
    result = _url_to_pattern("not-a-url")
    assert result == "not-a-url"


def test_two_digit_numeric_preserved() -> None:
    # /42 is 2-digit — should be kept (avoids collapsing /en, /de, /v1, etc.)
    assert _url_to_pattern("https://example.com/page/42") == "example.com/page/42"


def test_three_digit_numeric_collapsed() -> None:
    assert _url_to_pattern("https://example.com/page/123") == "example.com/page/{id}"
