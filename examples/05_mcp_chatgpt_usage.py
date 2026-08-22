"""
Example 5: Using Anansi via ChatGPT / OpenAI infrastructure.

Three integration paths are shown:

  A. ChatGPT Desktop App (macOS/Windows) — paste the config into
     Settings → Connectors → Add MCP Server.  No code required.

  B. OpenAI Agents SDK (programmatic, stdio) — spawn the Anansi MCP
     server as a local subprocess and drive it from Python code.
     Requires: pip install "anansi-scraper[openai]"
               OPENAI_API_KEY set in your environment

  C. Remote SSE transport — start Anansi as an HTTP server so any
     ChatGPT client (desktop or web) can reach it over the network.
     Requires: anansi-mcp --transport sse --host 0.0.0.0 --port 8000
"""

import asyncio
import json

# ── Shared example prompt ─────────────────────────────────────────────────────

EXAMPLE_PROMPT = """
Use the Anansi scraping tools to:
1. Fetch https://news.ycombinator.com/
2. Extract the top 5 story titles and scores using CSS selectors:
   - titles: ".titleline > a"
   - scores: ".score"
3. Return the results as a formatted list.
"""

# ── Path A: ChatGPT Desktop App ───────────────────────────────────────────────
#
# Open ChatGPT Desktop → Settings → Connectors → Add MCP Server, then paste:
#
CHATGPT_DESKTOP_CONFIG = {
    "command": "anansi-mcp",
    "args": [],
    "env": {},
}
#
# If `anansi-mcp` is not on PATH (common on Windows), use the full form:
CHATGPT_DESKTOP_CONFIG_FULL_PATH = {
    "command": "python",
    "args": ["-m", "anansi.mcp_server.server"],
    "env": {},
}


# ── Path B: OpenAI Agents SDK (programmatic, stdio) ───────────────────────────
#
# Install: pip install "anansi-scraper[openai]"
# Env:     OPENAI_API_KEY=<your-key>

async def run_with_agents_sdk() -> None:
    """Drive Anansi from the OpenAI Agents SDK using a local stdio MCP server."""
    from agents import Agent, Runner  # type: ignore[import]
    from agents.mcp import MCPServerStdio  # type: ignore[import]

    async with MCPServerStdio(
        params={"command": "anansi-mcp", "args": []}
    ) as mcp_server:
        agent = Agent(
            name="AnansiWebScraper",
            instructions=(
                "You are a web scraping assistant. "
                "Use the Anansi tools to fetch and extract web data as requested."
            ),
            mcp_servers=[mcp_server],
        )
        result = await Runner.run(agent, EXAMPLE_PROMPT)
        print(result.final_output)


# ── Path C: Remote SSE transport ──────────────────────────────────────────────
#
# First start the server in a terminal:
#   anansi-mcp --transport sse --host 0.0.0.0 --port 8000
#
# Then connect from the Agents SDK (or point ChatGPT Desktop at the URL):
#   SSE endpoint: http://<host>:8000/sse
#
# ChatGPT Desktop remote config (Settings → Connectors → Add MCP Server):
CHATGPT_REMOTE_CONFIG = {
    "url": "http://localhost:8000/sse",
}

async def run_with_remote_sse() -> None:
    """Connect to a remotely running Anansi MCP server via HTTP/SSE."""
    from agents import Agent, Runner  # type: ignore[import]
    from agents.mcp import MCPServerSse  # type: ignore[import]

    async with MCPServerSse(
        params={"url": "http://localhost:8000/sse"}
    ) as mcp_server:
        agent = Agent(
            name="AnansiWebScraper",
            instructions=(
                "You are a web scraping assistant. "
                "Use the Anansi tools to fetch and extract web data as requested."
            ),
            mcp_servers=[mcp_server],
        )
        result = await Runner.run(agent, EXAMPLE_PROMPT)
        print(result.final_output)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Anansi — ChatGPT / OpenAI Integration")
    print("=" * 50)

    print("\n── Path A: ChatGPT Desktop App ──")
    print("Paste into Settings → Connectors → Add MCP Server:")
    print(json.dumps(CHATGPT_DESKTOP_CONFIG, indent=2))

    print("\n── Path B: OpenAI Agents SDK (local stdio) ──")
    print("Install:  pip install 'anansi-scraper[openai]'")
    print("Run:      python examples/05_mcp_chatgpt_usage.py --run-agents")
    print()
    print("Example prompt:")
    print(EXAMPLE_PROMPT)

    print("── Path C: Remote SSE ──")
    print("Start server:  anansi-mcp --transport sse --host 0.0.0.0 --port 8000")
    print("ChatGPT Desktop remote config:")
    print(json.dumps(CHATGPT_REMOTE_CONFIG, indent=2))

    import sys
    if "--run-agents" in sys.argv:
        asyncio.run(run_with_agents_sdk())
    elif "--run-sse" in sys.argv:
        asyncio.run(run_with_remote_sse())
