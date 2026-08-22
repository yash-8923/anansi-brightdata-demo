"""Tests for crawl depth management."""

from __future__ import annotations

import httpx
import pytest
import respx

from anansi.core import Item, Request, Response
from anansi.spider.crawler import Crawler
from anansi.spider.spider import Spider

_LEVEL_0_HTML = """
<html><body>
  <a href="https://example.com/level1">level 1</a>
  <a href="https://example.com/level1b">level 1b</a>
</body></html>
"""

_LEVEL_1_HTML = """
<html><body>
  <h1 class="title">Level 1 Page</h1>
  <a href="https://example.com/level2">level 2 (should not fetch when max_depth=1)</a>
</body></html>
"""

_LEVEL_2_HTML = """
<html><body>
  <h1 class="title">Level 2 Page — should not be reached</h1>
</body></html>
"""


class DepthSpider(Spider):
    name = "depth_test"
    start_urls = ["https://example.com/"]

    async def parse(self, response: Response):
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        title_tag = response.css("h1.title")
        if title_tag:
            yield Item(data={"url": response.url, "title": title_tag[0].text})

        soup = BeautifulSoup(response.html, "lxml")
        for a in soup.find_all("a", href=True):
            href = urljoin(response.url, str(a["href"]))
            if href.startswith("https://example.com"):
                yield Request(url=href, callback="parse")


async def test_max_depth_limits_link_following(tmp_path) -> None:
    fetched_urls: list[str] = []

    with respx.mock:
        def record(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            fetched_urls.append(url)
            if url == "https://example.com/":
                return httpx.Response(200, text=_LEVEL_0_HTML)
            if "level1" in url:
                return httpx.Response(200, text=_LEVEL_1_HTML)
            return httpx.Response(200, text=_LEVEL_2_HTML)

        respx.get(url__regex=r"https://example\.com/.*").mock(side_effect=record)

        crawler = Crawler(
            DepthSpider,
            max_depth=1,
            delay=0.0,
            delay_jitter=0.0,
            domain_delay=0.0,
            respect_robots=False,
            auto_browser=False,
            db_path=tmp_path / "crawls.db",
            adaptive_rate_limiting=False,
        )
        items = [item async for item in crawler.run()]

    # level2 must never have been fetched
    assert not any("level2" in u for u in fetched_urls), (
        f"level2 was fetched despite max_depth=1: {fetched_urls}"
    )


async def test_no_max_depth_follows_all_levels(tmp_path) -> None:
    fetched_urls: list[str] = []

    with respx.mock:
        def record(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            fetched_urls.append(url)
            if url == "https://example.com/":
                return httpx.Response(200, text=_LEVEL_0_HTML)
            if "level1" in url and "level2" not in url:
                return httpx.Response(200, text=_LEVEL_1_HTML)
            return httpx.Response(200, text=_LEVEL_2_HTML)

        respx.get(url__regex=r"https://example\.com/.*").mock(side_effect=record)

        crawler = Crawler(
            DepthSpider,
            max_depth=None,
            delay=0.0,
            delay_jitter=0.0,
            domain_delay=0.0,
            respect_robots=False,
            auto_browser=False,
            db_path=tmp_path / "crawls.db",
            adaptive_rate_limiting=False,
        )
        _ = [item async for item in crawler.run()]

    assert any("level2" in u for u in fetched_urls), (
        f"level2 was never fetched when max_depth=None: {fetched_urls}"
    )


async def test_depth_stored_in_meta(tmp_path) -> None:
    """Child URLs pushed to the queue should have depth=parent_depth+1 in meta."""
    from anansi.db import crawl_db

    with respx.mock:
        respx.get("https://example.com/").mock(
            return_value=httpx.Response(200, text=_LEVEL_0_HTML)
        )
        respx.get(url__regex=r"https://example\.com/level.*").mock(
            return_value=httpx.Response(200, text="<html><body>leaf</body></html>")
        )

        db_path = tmp_path / "crawls.db"
        crawler = Crawler(
            DepthSpider,
            max_depth=None,
            delay=0.0,
            delay_jitter=0.0,
            domain_delay=0.0,
            respect_robots=False,
            auto_browser=False,
            db_path=db_path,
            adaptive_rate_limiting=False,
        )
        _ = [item async for item in crawler.run()]

    async with crawl_db(db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT url, meta FROM url_queue WHERE crawl_id = ?",
            (crawler.crawl_id,),
        )

    import json
    depth_by_url = {r["url"]: json.loads(r["meta"] or "{}").get("depth", 0) for r in rows}
    # All level1 URLs should have depth=1 in their stored meta
    level1_urls = [u for u in depth_by_url if "level1" in u]
    assert level1_urls, "No level1 URLs found in queue"
    for u in level1_urls:
        assert depth_by_url[u] == 1, f"Expected depth=1 for {u}, got {depth_by_url[u]}"
