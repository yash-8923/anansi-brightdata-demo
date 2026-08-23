"""Bright Data Scraper Studio collector client.

Anansi already owns fetching, parsing, self-healing (local CSS-selector
confidence scoring), anti-bot evasion, and crawling. This module does NOT
duplicate any of that. It adds one new capability Anansi doesn't have:
triggering a Bright Data Scraper Studio "Collector" — a scraper you build
once with the Bright Data CLI (``bdata scraper create``) that Bright Data's
own infrastructure runs and AI-heals server-side (``bdata scraper heal``).

Flow:
    1. You build the Collector once, outside of Python, with the Bright Data
       CLI (see SETUP.md). That step gives you a ``c_*`` Collector ID.
    2. This module calls ``POST /dca/trigger`` (or ``/dca/trigger_immediate``
       + poll) with that Collector ID from inside Anansi — e.g. from an MCP
       tool, a scheduled job, or a script — and maps the returned JSON rows
       into Anansi's existing ``Item`` dataclass.
    3. Everything downstream (dedup, storage, dashboard, MCP `get_crawl_items`
       equivalents) works with a normal Anansi ``Item``, so nothing else in
       the codebase needs to change.

Env vars (read once, never hardcoded, never logged):
    BRIGHTDATA_API_KEY       — Bright Data API token (Settings -> API keys)
    BRIGHTDATA_COLLECTOR_ID  — the c_* ID printed by `bdata scraper create`
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from anansi.core import Item

load_dotenv()  # reads .env in the current working directory, if present

logger = logging.getLogger(__name__)

TRIGGER_URL = "https://api.brightdata.com/dca/trigger_immediate"
RESULT_URL = "https://api.brightdata.com/dca/get_result"
SYNC_TRIGGER_URL = "https://api.brightdata.com/dca/trigger"

_DEFAULT_POLL_INTERVAL = 3.0
_DEFAULT_POLL_TIMEOUT = 180.0


class BrightDataCollectorError(Exception):
    """Raised for any non-2xx response or malformed payload from Bright Data."""


class BrightDataCollector:
    """Thin async client for one Bright Data Scraper Studio Collector.

    This class does not do any scraping itself — it is a trigger + result
    fetcher for a Collector you already created with the Bright Data CLI.
    """

    def __init__(
        self,
        api_key: str | None = None,
        collector_id: str | None = None,
        *,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        poll_timeout: float = _DEFAULT_POLL_TIMEOUT,
    ) -> None:
        self.api_key = api_key or os.environ.get("BRIGHTDATA_API_KEY")
        self.collector_id = collector_id or os.environ.get("BRIGHTDATA_COLLECTOR_ID")
        if not self.api_key:
            raise BrightDataCollectorError(
                "BRIGHTDATA_API_KEY is not set. Export it or pass api_key= explicitly."
            )
        if not self.collector_id:
            raise BrightDataCollectorError(
                "BRIGHTDATA_COLLECTOR_ID is not set. Create one with "
                "`bdata scraper create <url> \"<what to extract>\"` first."
            )
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def trigger(self, inputs: dict[str, Any] | list[dict[str, Any]] | None = None) -> str:
        """Kick off an async run. Returns a snapshot/job id to poll with ``wait_for_result``.

        Bright Data's /dca/trigger_immediate always expects an ARRAY of row
        objects, and each row must include a "url" key (even if your
        Collector was built against one fixed URL). Pass e.g.
        ``{"url": "https://example.com/page"}`` or a list of such dicts for
        multiple rows.
        """
        if inputs is None:
            raise BrightDataCollectorError(
                'inputs is required — pass e.g. {"url": "https://your-target/"} '
                "(Bright Data requires a url per row, even for single-URL collectors)."
            )
        payload = inputs if isinstance(inputs, list) else [inputs]
        for row in payload:
            if "url" not in row:
                raise BrightDataCollectorError(
                    f'Row missing required "url" key: {row}'
                )
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                TRIGGER_URL,
                headers=self._headers(),
                params={"collector": self.collector_id},
                json=payload,
            )
            if resp.status_code >= 400:
                raise BrightDataCollectorError(
                    f"trigger_immediate failed ({resp.status_code}): {resp.text[:500]}"
                )
            data = resp.json()
            snapshot_id = data.get("snapshot_id") or data.get("collection_id") or data.get("id")
            if not snapshot_id:
                raise BrightDataCollectorError(f"No snapshot id in response: {data}")
            logger.info("Bright Data collector %s triggered: %s", self.collector_id, snapshot_id)
            return str(snapshot_id)

    async def wait_for_result(self, snapshot_id: str) -> list[dict[str, Any]]:
        """Poll ``get_result`` until the run finishes, then return raw rows."""
        elapsed = 0.0
        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < self.poll_timeout:
                resp = await client.get(
                    RESULT_URL,
                    headers=self._headers(),
                    params={"id": snapshot_id},
                )
                if resp.status_code == 202:
                    await asyncio.sleep(self.poll_interval)
                    elapsed += self.poll_interval
                    continue
                if resp.status_code >= 400:
                    raise BrightDataCollectorError(
                        f"get_result failed ({resp.status_code}): {resp.text[:500]}"
                    )
                data = resp.json()
                if isinstance(data, dict) and data.get("status") in ("running", "pending"):
                    await asyncio.sleep(self.poll_interval)
                    elapsed += self.poll_interval
                    continue
                return data if isinstance(data, list) else data.get("results", [])
        raise BrightDataCollectorError(
            f"Timed out after {self.poll_timeout}s waiting for snapshot {snapshot_id}"
        )

    async def run(self, inputs: dict[str, Any] | None = None) -> list[Item]:
        """Trigger the collector, wait for results, and return Anansi Items.

        ``inputs`` must include a "url" key, e.g. {"url": "https://your-target/"}.
        This is the one call most integrations need: fire-and-collect.
        """
        snapshot_id = await self.trigger(inputs)
        rows = await self.wait_for_result(snapshot_id)
        return self._rows_to_items(rows)

    async def run_sync(self, inputs: dict[str, Any] | None = None) -> list[Item]:
        """Use the 25-50s synchronous ``/dca/trigger`` path for small/fast targets."""
        if inputs is None or "url" not in inputs:
            raise BrightDataCollectorError(
                'inputs must include a "url" key, e.g. {"url": "https://your-target/"}.'
            )
        payload = [inputs]
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                SYNC_TRIGGER_URL,
                headers=self._headers(),
                params={"collector": self.collector_id},
                json=payload,
            )
            if resp.status_code >= 400:
                raise BrightDataCollectorError(
                    f"sync trigger failed ({resp.status_code}): {resp.text[:500]}"
                )
            data = resp.json()
        rows = data if isinstance(data, list) else data.get("results", [])
        return self._rows_to_items(rows)

    def _rows_to_items(self, rows: list[dict[str, Any]]) -> list[Item]:
        items: list[Item] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            items.append(
                Item(
                    data=row,
                    source_url=row.get("url", "") or row.get("source_url", ""),
                    spider_name=f"brightdata:{self.collector_id}",
                )
            )
        logger.info(
            "Bright Data collector %s returned %d item(s)", self.collector_id, len(items)
        )
        return items