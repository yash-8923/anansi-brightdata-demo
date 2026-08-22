"""
Anansi + Bright Data dashboard — a glance, not a UI you live in.

Per the hackathon's own guidance: "The terminal is the UI... the dashboard
is for a glance to confirm your Collector ID exists, or to set a schedule."
This intentionally does one thing: show that BRIGHTDATA_COLLECTOR_ID is wired
into something real (a live web page reading a live SQLite table), and let
you re-trigger a run with one button.

Run:
    python dashboard/app.py
Then open http://127.0.0.1:5050
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from flask import Flask, jsonify, render_template_string

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anansi.collectors.brightdata import BrightDataCollector, BrightDataCollectorError
from anansi.collectors.storage import count_runs, load_items, save_items

app = Flask(__name__)

PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Anansi × Bright Data</title>
  <style>
    body { font-family: -apple-system, Segoe UI, sans-serif; max-width: 900px; margin: 40px auto; color: #1a1a1a; }
    h1 { font-size: 22px; }
    .badge { display: inline-block; background: #10b981; color: white; padding: 3px 10px; border-radius: 12px; font-size: 13px; }
    .badge.missing { background: #ef4444; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #e5e5e5; font-size: 13px; vertical-align: top; }
    th { color: #666; font-weight: 600; }
    button { padding: 8px 16px; border: none; background: #111; color: white; border-radius: 6px; cursor: pointer; }
    code { background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>Anansi × Bright Data Scraper Studio</h1>
  <p>
    Collector ID:
    {% if collector_id %}
      <code>{{ collector_id }}</code> <span class="badge">wired</span>
    {% else %}
      <span class="badge missing">not set</span> — set BRIGHTDATA_COLLECTOR_ID
    {% endif %}
  </p>
  <p>Stored rows from Bright Data runs: <strong>{{ total }}</strong></p>
  <button onclick="fetch('/trigger', {method:'POST'}).then(()=>location.reload())">
    Trigger collector now
  </button>
  <table>
    <tr><th>Collector</th><th>Source URL</th><th>Data</th><th>Fetched</th></tr>
    {% for row in rows %}
    <tr>
      <td>{{ row.collector_id }}</td>
      <td>{{ row.source_url }}</td>
      <td><pre style="white-space:pre-wrap;margin:0">{{ row.data }}</pre></td>
      <td>{{ row.fetched_at }}</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""


@app.route("/")
def index():
    rows = load_items(limit=25)
    return render_template_string(
        PAGE,
        collector_id=os.environ.get("BRIGHTDATA_COLLECTOR_ID"),
        total=count_runs(),
        rows=rows,
    )


@app.route("/trigger", methods=["POST"])
def trigger():
    try:
        collector = BrightDataCollector()
        items = asyncio.run(collector.run())
        stored = save_items(items)
        return jsonify({"ok": True, "stored": stored})
    except BrightDataCollectorError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
