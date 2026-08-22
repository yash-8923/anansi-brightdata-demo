"""
Example 3: Full-scale concurrent crawl with proxy rotation and pause/resume.

This is the "few lines of Python" demo — a complete production-grade crawl
with concurrency, proxy rotation, adaptive extraction, and pause/resume.
"""

import asyncio
from anansi import Crawler, ProxyManager
from anansi.core import Item, Request, Response
from anansi.spider.spider import Spider, rule
from anansi.parser.adaptive import AdaptiveParser, SelectorConfig


class HackerNewsSpider(Spider):
    name = "hackernews"
    start_urls = ["https://news.ycombinator.com/"]

    # Follow links to story pages
    @rule(r"https://news\.ycombinator\.com/item\?id=\d+", callback="parse_story")
    async def parse(self, response: Response):
        """Extract story links from the front page."""
        for anchor in response.css("a.storylink, a.titlelink"):
            href = response.urljoin(anchor.get("href", ""))
            if href:
                yield Request(url=href, callback="parse_story")

        # Follow "More" pagination
        more = response.css("a.morelink")
        if more:
            yield Request(url=response.urljoin(more[0]["href"]), callback="parse")

    async def parse_story(self, response: Response):
        parser = AdaptiveParser()
        data = await parser.extract(
            response.html,
            {
                "title": SelectorConfig("title", expected_pattern=r"\w{3,}"),
                "score": SelectorConfig(".score", expected_pattern=r"\d+ points?"),
                "author": SelectorConfig(".hnuser, .by a"),
                "comments": SelectorConfig(".subtext a[href*=item]", expected_pattern=r"\d+"),
            },
            url=response.url,
        )
        if data.get("title"):
            yield Item(
                data={**data, "url": response.url},
                source_url=response.url,
                spider_name=self.name,
            )


async def main():
    # Optional: rotate through proxies
    # proxy_manager = ProxyManager([
    #     "http://proxy1:8080",
    #     "socks5://proxy2:1080",
    # ])

    crawler = Crawler(
        HackerNewsSpider,
        concurrency=5,       # 5 simultaneous requests
        delay=0.5,           # 0.5s base delay between requests
        max_pages=20,        # stop after 20 pages (demo limit)
        # proxy_manager=proxy_manager,
    )

    print(f"Crawl ID: {crawler.crawl_id}")
    print("Starting crawl... (Ctrl+C to pause)\n")

    items_seen = 0
    try:
        async for item in crawler.run():
            items_seen += 1
            print(f"[{items_seen}] {item.data.get('title', 'N/A')[:60]}")
            print(f"     score={item.data.get('score')}  author={item.data.get('author')}")
            print(f"     {item.source_url[:80]}\n")
    except KeyboardInterrupt:
        print(f"\nPaused. Crawl ID: {crawler.crawl_id}")
        print("Resume with: Crawler.resume('<crawl_id>', HackerNewsSpider)")

    print(f"\nDone. {items_seen} items collected.")


if __name__ == "__main__":
    asyncio.run(main())
