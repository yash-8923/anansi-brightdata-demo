"""
Example 2: Adaptive parser with selector healing.

Demonstrates how the parser learns which selectors work for a URL pattern
and automatically heals them when the page structure changes.
"""

import asyncio
from anansi import AdaptiveParser
from anansi.parser.adaptive import SelectorConfig

HTML_V1 = """
<html><body>
  <article>
    <h1 class="article-title post-title">Hello World</h1>
    <span class="post-price price">$29.99</span>
    <div class="post-body">This is the article body text.</div>
  </article>
</body></html>
"""

# Simulated page redesign: class names changed
HTML_V2 = """
<html><body>
  <article>
    <h1 class="story-heading content-title">Hello World</h1>
    <span class="product-cost amount">$29.99</span>
    <div class="story-body main-content">This is the article body text.</div>
  </article>
</body></html>
"""

SELECTORS = {
    "title": SelectorConfig(
        selector="h1.article-title",
        expected_pattern=r"[A-Z][a-z]",  # title-cased text helps healing
    ),
    "price": SelectorConfig(
        selector=".post-price",
        expected_pattern=r"\$[\d,.]+",   # dollar amount regex helps healing
    ),
    "body": ".post-body",                # plain string selector also works
}


async def main():
    parser = AdaptiveParser()

    print("=== Parsing V1 (exact selectors) ===")
    data_v1 = await parser.extract(HTML_V1, SELECTORS, url="https://example.com/posts/42")
    for k, v in data_v1.items():
        print(f"  {k}: {v!r}")

    print("\n=== Parsing V2 (page redesign — selectors must heal) ===")
    data_v2 = await parser.extract(HTML_V2, SELECTORS, url="https://example.com/posts/43")
    for k, v in data_v2.items():
        print(f"  {k}: {v!r}")

    print("\n=== Selector knowledge for 'price' ===")
    known = await parser.known_selectors("example.com/posts/{id}", "price")
    for sel in known:
        print(f"  {sel['selector']!r}  confidence={sel['confidence']:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
