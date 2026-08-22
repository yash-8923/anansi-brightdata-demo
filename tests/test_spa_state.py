"""Tests for SPA initial state extraction (Next.js / Nuxt / Redux)."""

from __future__ import annotations

import httpx
import pytest
import respx

from anansi.parser.structured import extract_spa_state
from bs4 import BeautifulSoup


_NEXT_JS_HTML = """
<html>
<head><title>Next.js App</title></head>
<body>
<div id="__next"><p>SSR content</p></div>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"title":"Hello","items":[1,2,3]}},"page":"/","query":{},"buildId":"abc123"}
</script>
</body>
</html>
"""

_NUXT_HTML = """
<html>
<body>
<script>window.__NUXT__={"data":[{"message":"Hello from Nuxt"}],"state":{}}</script>
</body>
</html>
"""

_INITIAL_STATE_HTML = """
<html>
<body>
<script>window.__INITIAL_STATE__={"user":{"id":42,"name":"Alice"},"theme":"dark"};</script>
</body>
</html>
"""

_PRELOADED_STATE_HTML = """
<html>
<body>
<script>window.__PRELOADED_STATE__={"cart":{"items":[],"total":0}};</script>
</body>
</html>
"""

_MALFORMED_JSON_HTML = """
<html>
<body>
<script id="__NEXT_DATA__" type="application/json">
{this is not valid json
</script>
</body>
</html>
"""

_NO_SPA_HTML = """
<html>
<body>
<p>Just a regular page, no SPA state here.</p>
<script>console.log("hello");</script>
</body>
</html>
"""


def _parse(html: str) -> dict:
    return extract_spa_state(BeautifulSoup(html, "lxml"))


def test_next_js_data_extracted() -> None:
    result = _parse(_NEXT_JS_HTML)
    assert "next_data" in result
    assert result["next_data"]["page"] == "/"
    assert result["next_data"]["props"]["pageProps"]["title"] == "Hello"


def test_nuxt_state_extracted() -> None:
    result = _parse(_NUXT_HTML)
    assert "nuxt" in result
    assert result["nuxt"]["data"][0]["message"] == "Hello from Nuxt"


def test_initial_state_extracted() -> None:
    result = _parse(_INITIAL_STATE_HTML)
    assert "initial_state" in result
    assert result["initial_state"]["user"]["name"] == "Alice"


def test_preloaded_state_extracted() -> None:
    result = _parse(_PRELOADED_STATE_HTML)
    assert "preloaded_state" in result
    assert result["preloaded_state"]["cart"]["total"] == 0


def test_malformed_json_returns_empty_no_exception() -> None:
    result = _parse(_MALFORMED_JSON_HTML)
    assert "next_data" not in result


def test_no_markers_returns_empty_dict() -> None:
    result = _parse(_NO_SPA_HTML)
    assert result == {}


def test_no_markers_no_beautifulsoup_parse() -> None:
    """Performance: if no markers are present, extract_spa_state returns {} immediately."""
    html = "<html><body><p>plain</p></body></html>"
    soup = BeautifulSoup(html, "lxml")
    result = extract_spa_state(soup)
    assert result == {}


async def test_http_fetcher_populates_spa_state() -> None:
    """HTTPFetcher should populate FetchResult.spa_state for Next.js pages."""
    from anansi.fetchers.http import HTTPFetcher

    with respx.mock:
        respx.get("https://example.com/").mock(
            return_value=httpx.Response(200, text=_NEXT_JS_HTML)
        )
        async with HTTPFetcher() as fetcher:
            result = await fetcher.fetch("https://example.com/")

    assert result.spa_state is not None
    assert "next_data" in result.spa_state


async def test_http_fetcher_no_spa_state_for_plain_html() -> None:
    """HTTPFetcher should return spa_state=None for pages without SPA markers."""
    from anansi.fetchers.http import HTTPFetcher

    with respx.mock:
        respx.get("https://example.com/").mock(
            return_value=httpx.Response(200, text=_NO_SPA_HTML)
        )
        async with HTTPFetcher() as fetcher:
            result = await fetcher.fetch("https://example.com/")

    assert result.spa_state is None


async def test_crawler_response_has_spa_state(tmp_path) -> None:
    """spa_state should be propagated to spider Response objects."""
    from anansi.core import Item, Response as SpiderResponse
    from anansi.spider.crawler import Crawler
    from anansi.spider.spider import Spider

    captured: list[dict] = []

    class _S(Spider):
        name = "spa_crawl"
        start_urls = ["https://example.com/"]

        async def parse(self, response: SpiderResponse):
            captured.append(response.spa_state)
            return
            yield  # noqa: unreachable

    with respx.mock:
        respx.get("https://example.com/").mock(
            return_value=httpx.Response(200, text=_NEXT_JS_HTML)
        )

        crawler = Crawler(
            _S,
            delay=0.0,
            delay_jitter=0.0,
            domain_delay=0.0,
            respect_robots=False,
            auto_browser=False,
            db_path=tmp_path / "crawls.db",
            adaptive_rate_limiting=False,
        )
        _ = [item async for item in crawler.run()]

    assert captured, "parse() was never called"
    assert captured[0] is not None
    assert "next_data" in captured[0]
