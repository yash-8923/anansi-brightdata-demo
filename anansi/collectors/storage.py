"""Tiny SQLite store for Bright Data Collector runs — deliberately separate
from anansi/db.py (Anansi's crawl-state DB) so this integration never touches
core schema/migrations. One table, no migrations, safe to delete anytime.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from anansi.core import Item

DB_PATH = Path.home() / ".anansi" / "brightdata.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS brightdata_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collector_id TEXT NOT NULL,
    source_url TEXT,
    data TEXT NOT NULL,
    fetched_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_brightdata_collector ON brightdata_items(collector_id);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def save_items(items: list[Item]) -> int:
    """Persist Items from a Bright Data run. Returns count written."""
    if not items:
        return 0
    conn = _connect()
    try:
        now = time.time()
        conn.executemany(
            "INSERT INTO brightdata_items (collector_id, source_url, data, fetched_at) "
            "VALUES (?, ?, ?, ?)",
            [
                (item.spider_name, item.source_url, json.dumps(item.data), now)
                for item in items
            ],
        )
        conn.commit()
        return len(items)
    finally:
        conn.close()


def load_items(collector_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        if collector_id:
            cur = conn.execute(
                "SELECT collector_id, source_url, data, fetched_at FROM brightdata_items "
                "WHERE collector_id = ? ORDER BY id DESC LIMIT ?",
                (collector_id, limit),
            )
        else:
            cur = conn.execute(
                "SELECT collector_id, source_url, data, fetched_at FROM brightdata_items "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "collector_id": r[0],
            "source_url": r[1],
            "data": json.loads(r[2]),
            "fetched_at": r[3],
        }
        for r in rows
    ]


def count_runs() -> int:
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM brightdata_items").fetchone()[0]
    finally:
        conn.close()
