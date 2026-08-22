"""Tests for AdaptiveParser."""

from __future__ import annotations

from pathlib import Path

import pytest

from anansi.parser.adaptive import AdaptiveParser, SelectorConfig

_PRODUCT_HTML = """
<html>
<head>
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"Product","name":"Widget Pro","price":"29.99"}
  </script>
</head>
<body>
  <h1 class="product-title">Widget Pro</h1>
  <span class="product-price">$29.99</span>
  <p class="description">A great widget.</p>
</body>
</html>
"""

_NO_STRUCTURED_HTML = """
<html><body>
  <h1 class="article-title">Test Article</h1>
  <p class="byline">By Jane</p>
</body></html>
"""


async def test_css_selector_extracts_text(tmp_sel_db: Path) -> None:
    parser = AdaptiveParser(db_path=tmp_sel_db)
    result = await parser.extract(
        _NO_STRUCTURED_HTML,
        {"title": ".article-title", "author": ".byline"},
        url="https://blog.example.com/posts/1",
    )
    assert result["title"] == "Test Article"
    assert result["author"] == "By Jane"


async def test_json_ld_short_circuits_css(tmp_sel_db: Path) -> None:
    parser = AdaptiveParser(db_path=tmp_sel_db)
    result = await parser.extract(
        _PRODUCT_HTML,
        {"name": ".product-title", "price": ".product-price"},
        url="https://shop.example.com/products/1",
        use_structured=True,
    )
    # JSON-LD supplies name and price at confidence 0.95 — CSS should not run
    assert result["name"] == "Widget Pro"
    assert result["price"] == "29.99"


async def test_missing_selector_returns_none(tmp_sel_db: Path) -> None:
    parser = AdaptiveParser(db_path=tmp_sel_db)
    result = await parser.extract(
        _NO_STRUCTURED_HTML,
        {"nonexistent": ".does-not-exist"},
        url="https://example.com/x",
    )
    assert result["nonexistent"] is None


async def test_selector_config_attribute_extraction(tmp_sel_db: Path) -> None:
    html = '<html><body><a class="main-link" href="https://target.com">click</a></body></html>'
    parser = AdaptiveParser(db_path=tmp_sel_db)
    result = await parser.extract(
        html,
        {"link": SelectorConfig(".main-link", attribute="href")},
        url="https://example.com/page",
    )
    assert result["link"] == "https://target.com"


async def test_multiple_values(tmp_sel_db: Path) -> None:
    html = """
    <html><body>
      <ul>
        <li class="tag">python</li>
        <li class="tag">scraping</li>
        <li class="tag">async</li>
      </ul>
    </body></html>
    """
    parser = AdaptiveParser(db_path=tmp_sel_db)
    result = await parser.extract(
        html,
        {"tags": SelectorConfig(".tag", multiple=True)},
        url="https://example.com/article",
    )
    assert isinstance(result["tags"], list)
    assert len(result["tags"]) == 3
    assert "python" in result["tags"]


async def test_extract_structured_returns_json_ld(tmp_sel_db: Path) -> None:
    parser = AdaptiveParser(db_path=tmp_sel_db)
    sd = await parser.extract_structured(_PRODUCT_HTML)
    assert any(obj.get("name") == "Widget Pro" for obj in sd["json_ld"])
