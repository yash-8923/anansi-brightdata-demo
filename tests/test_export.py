"""Tests for export_items CSV serialization of nested structures."""

from __future__ import annotations

import csv
import io
import json

import pytest

from anansi.spider.crawler import Crawler
from anansi.spider.spider import Spider


class _MinimalSpider(Spider):
    name = "export_test"
    start_urls = ["https://example.com/"]


async def _make_crawler(tmp_path):
    return Crawler(
        _MinimalSpider,
        delay=0.0,
        delay_jitter=0.0,
        domain_delay=0.0,
        respect_robots=False,
        auto_browser=False,
        db_path=tmp_path / "crawls.db",
        adaptive_rate_limiting=False,
    )


async def _seed_items(crawler, items):
    """Insert items directly into DB for export testing."""
    from anansi.db import crawl_db
    from anansi.spider.crawler import CrawlState
    await crawler._upsert_crawl(crawler._spider_cls().name, CrawlState.RUNNING)
    async with crawl_db(crawler._db_path) as db:
        for item in items:
            await db.execute(
                "INSERT INTO items (crawl_id, data, source_url, spider_name) VALUES (?, ?, ?, ?)",
                (crawler.crawl_id, json.dumps(item), "https://example.com/", "export_test"),
            )
        await db.commit()


async def test_csv_nested_dict_serialized_as_json(tmp_path) -> None:
    crawler = await _make_crawler(tmp_path)
    await _seed_items(crawler, [{"meta": {"k": "v"}, "title": "hello"}])

    csv_text = await Crawler.export_items(crawler.crawl_id, fmt="csv", db_path=crawler._db_path)
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == 1
    # The dict value should be valid JSON, not Python repr
    parsed = json.loads(rows[0]["meta"])
    assert parsed == {"k": "v"}


async def test_csv_nested_list_serialized_as_json(tmp_path) -> None:
    crawler = await _make_crawler(tmp_path)
    await _seed_items(crawler, [{"tags": ["a", "b", "c"]}])

    csv_text = await Crawler.export_items(crawler.crawl_id, fmt="csv", db_path=crawler._db_path)
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == 1
    parsed = json.loads(rows[0]["tags"])
    assert parsed == ["a", "b", "c"]


async def test_csv_none_value_becomes_empty_string(tmp_path) -> None:
    crawler = await _make_crawler(tmp_path)
    await _seed_items(crawler, [{"title": "hi", "optional": None}])

    csv_text = await Crawler.export_items(crawler.crawl_id, fmt="csv", db_path=crawler._db_path)
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0]["optional"] == ""


async def test_csv_empty_crawl_returns_empty_string(tmp_path) -> None:
    crawler = await _make_crawler(tmp_path)
    from anansi.spider.crawler import CrawlState
    await crawler._upsert_crawl(crawler._spider_cls().name, CrawlState.RUNNING)

    csv_text = await Crawler.export_items(crawler.crawl_id, fmt="csv", db_path=crawler._db_path)
    assert csv_text == ""
