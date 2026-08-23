# Setup — WBS Scraper + Bright Data Scraper Studio

This project combines two self-healing layers:

- **WBS Scraper** (this repo) — local, code-level self-healing: CSS selectors carry
  confidence scores and repair themselves, a headless browser kicks in
  silently when a page needs JS rendering, and a coherent anti-bot identity
  (TLS fingerprint, persona, vendor-aware Cloudflare/Akamai/DataDome handling)
  works to get through hostile sites.
- **Bright Data Scraper Studio** — a Collector (`c_*` ID) you build once with
  the Bright Data CLI, run from anywhere with a single API trigger, and
  self-heal with `bdata scraper heal` when the target site's HTML changes,
  entirely on Bright Data's side — no redeploy, same Collector ID.

WBS Scraper's crawler/parser/anti-bot code is untouched by this integration. The
new code lives entirely in `WBS Scraper/collectors/` and two new MCP tools
(`brightdata_run`, `brightdata_items`) plus a small dashboard.

---

## 0. Prerequisites

- Python 3.11+
- Node.js (only needed to run the Bright Data CLI via `npx`, nothing to install globally)
- A Bright Data account with credits (you already have this — $50 hackathon credit)

---

## 1. Install this project

```bash
git clone <your-fork-url> WBS Scraper
cd WBS Scraper
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dashboard]"    # core deps + Flask for the dashboard
playwright install chromium      # for WBS Scraper's browser-fallback fetcher
```

Copy the env template and fill in your Bright Data API key (Collector ID comes in step 3):

```bash
cp .env.example .env
```

Get your API key from the Bright Data dashboard: **Settings → API keys**.
Put it in `.env` as `BRIGHTDATA_API_KEY`. Load it into your shell before running anything:

```bash
export $(cat .env | grep -v '^#' | xargs)
```

---

## 2. Pick a target site

Per the hackathon rules: **do not** target a site already covered by Bright
Data's 800+ pre-built scrapers (Amazon, LinkedIn, big e-commerce, etc). Pick
something in the long tail — a regional e-commerce site, a niche B2B catalog,
a docs/changelog page, a smaller marketplace. If a judge would ask "why not
just use the pre-built scraper," pick a different target.

---

## 3. Create your Scraper Studio Collector (this is the required part)

Run the Bright Data CLI directly — no install needed, `npx` fetches it on demand:

```bash
npx -p @brightdata/cli bdata login
```

This opens a browser for OAuth once. Then create the scraper from a URL and a
plain-language description of what to extract:

```bash
npx -p @brightdata/cli bdata scraper create \
  "https://your-target-site.com/some-page" \
  "Extract title, price, and availability for each listed item"
```

This takes 5–15 minutes (up to 25 for complex sites) while Bright Data's AI
generates the scraper. It polls automatically — just wait. On success it
prints a **Collector ID** starting with `c_` — this is your proof of using
Scraper Studio. Copy it into `.env`:

```
BRIGHTDATA_COLLECTOR_ID=c_xxxxxxxxxxxx
```

Verify it works from the CLI directly:

```bash
npx -p @brightdata/cli bdata scraper run c_xxxxxxxxxxxx "https://your-target-site.com/some-page"
```

You should get clean JSON back.

---

## 4. Run it from inside WBS Scraper

### Option A — MCP tool (agent-driven, "terminal is the UI")

Register the MCP server with your coding agent:

```bash
claude mcp add WBS Scraper -- WBS Scraper-mcp
```

Then, in conversation with your agent:

> "Run the Bright Data collector and show me what it found."

This calls the new `brightdata_run` tool, which triggers your Collector,
waits for results, maps them into WBS Scraper's `Item` model, and stores them.
`brightdata_items` reads them back later.

### Option B — Direct script

```python
import asyncio
from WBS Scraper.collectors.brightdata import BrightDataCollector
from WBS Scraper.collectors.storage import save_items

async def main():
    collector = BrightDataCollector()   # reads BRIGHTDATA_API_KEY / _COLLECTOR_ID from env
    items = await collector.run()
    save_items(items)
    for item in items:
        print(item.data)

asyncio.run(main())
```

### Option C — Dashboard (glance only, per hackathon guidance)

```bash
python dashboard/app.py
```

Open http://127.0.0.1:5050 — shows your Collector ID is wired up, the stored
rows, and a "Trigger collector now" button. This is intentionally minimal —
the CLI/agent is the real workflow, the dashboard is just the glance-check.

---

## 5. Demonstrate self-healing (judges will look for this specifically)

After your Collector is running, simulate/observe a site change and heal it
**without touching downstream code or the Collector ID**:

```bash
npx -p @brightdata/cli bdata scraper heal c_xxxxxxxxxxxx \
  "The price field returns null — the selector may have moved." \
  --url "https://your-target-site.com/some-page" \
  --pretty -o heal.json
```

This stops at an approval gate by default (human-in-the-loop). Review
`heal.json`'s `preview_result`, then commit:

```bash
npx -p @brightdata/cli bdata scraper approve c_xxxxxxxxxxxx \
  --url "https://your-target-site.com/some-page"
```

Or fully autonomous, no manual review (fine for a demo video):

```bash
npx -p @brightdata/cli bdata scraper heal c_xxxxxxxxxxxx \
  "Reviews stopped extracting after the page redesign" --auto-approve
```

Same Collector ID before and after — nothing downstream (WBS Scraper's tools,
storage, dashboard) needs to change. **Record this for the demo video.**

---

## 5b. Undeniable self-heal demo (recommended — do this instead of step 5 if your real target won't break on cue)

Your real target site probably won't redesign itself mid-hackathon, so judges
can tell when a "self-heal" is just a staged schema extension. Fix: host a
page you control, break it on camera, heal it on camera.

This repo ships one: `demo-target/`.

1. **Publish it.** Push this repo (or just the `demo-target/` folder) to
   GitHub Pages, or any static host. Note the live URL, e.g.
   `https://you.github.io/demo-target/`.

2. **Create the Collector against the healthy page:**
   ```bash
   npx -p @brightdata/cli bdata scraper create \
     "https://you.github.io/demo-target/" \
     "Extract title, price, and stock status for each listing"
   ```
   Run it, confirm 3 clean items with title/price/stock.

3. **Break it live:**
   ```bash
   cd demo-target
   ./break.sh break
   git add -A && git commit -m "break demo page" && git push
   ```
   This swaps in `index-broken.html` — renamed classes, price nested one
   level deeper. Re-run the scraper; price and title now come back null.

4. **Heal it live, same Collector ID:**
   ```bash
   npx -p @brightdata/cli bdata scraper heal <collector_id> \
     "Title class renamed to product-name, price moved into a nested span" \
     --url "https://you.github.io/demo-target/" --pretty -o heal.json
   ```
   Review `heal.json`'s `preview_result`, then:
   ```bash
   npx -p @brightdata/cli bdata scraper approve <collector_id> \
     --url "https://you.github.io/demo-target/"
   ```
   Re-run the scraper — all 3 fields populated again, same Collector ID,
   nothing in WBS Scraper or the dashboard touched.

5. **Restore for repeat demos:**
   ```bash
   ./break.sh restore
   git add -A && git commit -m "restore demo page" && git push
   ```

This is a real break + real heal, filmable end-to-end in under 90 seconds.

---

## 6. What to show in the demo video

1. WBS Scraper's own local self-healing (existing feature — `docs/how-it-works.md`
   has a walkthrough) — this is your code-owned layer.
2. `bdata scraper create` → Collector ID appears.
3. `brightdata_run` (via agent or script) → structured JSON, stored.
4. `bdata scraper heal` fixing a broken field → `bdata scraper approve` →
   re-run with the *same* Collector ID → data flows again, nothing downstream
   touched.
5. Dashboard glance confirming the Collector ID and stored rows.

---

## Security notes

- Never commit `.env` or your real API key. `.env` is already gitignored.
- Mask your API key on screen during the demo recording, or use a throwaway
  key you rotate afterward.
- Only scrape publicly available pages — no login walls, no paywalled
  content, no personal data (also enforced by WBS Scraper's own `robots.py` /
  `security.py`, and Bright Data's own ToS).
