"""Tests for SQLiteQueue."""

from __future__ import annotations

import pytest

from anansi.spider.queue import SQLiteQueue

from .conftest import CRAWL_ID


async def test_push_returns_true_on_first_insert(queue: SQLiteQueue) -> None:
    inserted = await queue.push("https://example.com/a")
    assert inserted is True


async def test_push_returns_false_on_duplicate(queue: SQLiteQueue) -> None:
    await queue.push("https://example.com/a")
    inserted = await queue.push("https://example.com/a")
    assert inserted is False


async def test_pop_returns_none_on_empty_queue(queue: SQLiteQueue) -> None:
    result = await queue.pop()
    assert result is None


async def test_pop_returns_url_and_callback(queue: SQLiteQueue) -> None:
    await queue.push("https://example.com/page", callback="parse_page")
    entry = await queue.pop()
    assert entry is not None
    url, callback, meta = entry
    assert url == "https://example.com/page"
    assert callback == "parse_page"


async def test_pop_advances_status_to_processing(queue: SQLiteQueue) -> None:
    from anansi.db import crawl_db

    await queue.push("https://example.com/p")
    await queue.pop()
    async with crawl_db(queue._db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT status FROM url_queue WHERE crawl_id=? AND url=?",
            (CRAWL_ID, "https://example.com/p"),
        )
    assert rows[0]["status"] == "processing"


async def test_meta_survives_round_trip(queue: SQLiteQueue) -> None:
    meta = {"depth": 3, "use_browser": True, "custom": "value"}
    await queue.push("https://example.com/meta", meta=meta)
    entry = await queue.pop()
    assert entry is not None
    _, _, returned_meta = entry
    assert returned_meta["depth"] == 3
    assert returned_meta["use_browser"] is True
    assert returned_meta["custom"] == "value"


async def test_increment_retry_requeues_under_budget(queue: SQLiteQueue) -> None:
    from anansi.db import crawl_db

    await queue.push("https://example.com/r")
    await queue.pop()  # move to processing
    await queue.increment_retry("https://example.com/r", max_retries=3)
    async with crawl_db(queue._db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT status, retry_count FROM url_queue WHERE crawl_id=? AND url=?",
            (CRAWL_ID, "https://example.com/r"),
        )
    assert rows[0]["status"] == "pending"
    assert rows[0]["retry_count"] == 1


async def test_increment_retry_fails_at_budget(queue: SQLiteQueue) -> None:
    from anansi.db import crawl_db

    await queue.push("https://example.com/fail")
    for _ in range(3):
        await queue.pop()
        await queue.increment_retry("https://example.com/fail", max_retries=3)
    async with crawl_db(queue._db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT status FROM url_queue WHERE crawl_id=? AND url=?",
            (CRAWL_ID, "https://example.com/fail"),
        )
    assert rows[0]["status"] == "failed"


async def test_requeue_stale_resets_processing(queue: SQLiteQueue) -> None:
    from anansi.db import crawl_db

    await queue.push("https://example.com/stale")
    await queue.pop()  # mark as processing
    recovered = await queue.requeue_stale()
    assert recovered == 1
    async with crawl_db(queue._db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT status FROM url_queue WHERE crawl_id=? AND url=?",
            (CRAWL_ID, "https://example.com/stale"),
        )
    assert rows[0]["status"] == "pending"


async def test_mark_visited_and_is_visited(queue: SQLiteQueue) -> None:
    url = "https://example.com/visited"
    assert not await queue.is_visited(url)
    await queue.mark_visited(url)
    assert await queue.is_visited(url)


async def test_pending_count(queue: SQLiteQueue) -> None:
    assert await queue.pending_count() == 0
    await queue.push("https://example.com/c1")
    await queue.push("https://example.com/c2")
    assert await queue.pending_count() == 2
