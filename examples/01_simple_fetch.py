"""
Example 1: Simple single-page fetch.

Shows the two fetchers side by side — lightweight HTTP and full browser.
"""

import asyncio
from anansi import HTTPFetcher, BrowserFetcher


async def main():
    url = "https://httpbin.org/headers"

    # ── HTTP fetch (fast, no JS) ──────────────────────────────────────────────
    async with HTTPFetcher() as fetcher:
        result = await fetcher.fetch(url)
        print(f"[HTTP] status={result.status}  elapsed={result.elapsed:.2f}s")
        print(result.html[:500])

    # ── Browser fetch (JS rendered, stealth mode) ─────────────────────────────
    # Uncomment if playwright is installed:
    #
    # async with BrowserFetcher(headless=True) as fetcher:
    #     result = await fetcher.fetch(url)
    #     print(f"[Browser] status={result.status}  elapsed={result.elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
