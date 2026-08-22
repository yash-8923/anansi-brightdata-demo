"""
Example 4: Using Anansi via the Claude API (tool use).

Shows how an LLM can use Anansi's MCP tools to scrape and extract data.
This is a standalone script that calls the Claude API with the Anansi
MCP server attached — no separate server process needed.
"""

# To run this example you need:
#   pip install anthropic
#   ANTHROPIC_API_KEY set in your environment
#
# Then start the MCP server in one terminal:
#   anansi-mcp
#
# And add it to your Claude Code config:
#   claude mcp add anansi -- anansi-mcp
#
# Alternatively, the snippet below shows programmatic MCP client usage
# via the anthropic SDK's MCP integration (requires anthropic>=0.40).

EXAMPLE_PROMPT = """
Use the Anansi scraping tools to:
1. Fetch https://news.ycombinator.com/
2. Extract the top 5 story titles and their scores using CSS selectors:
   - titles: ".titleline > a"
   - scores: ".score"
3. Return the results as a formatted list.
"""

# MCP server config for claude_code ~/.claude/claude_code_config.json:
MCP_CONFIG = {
    "mcpServers": {
        "anansi": {
            "command": "anansi-mcp",
            "args": [],
            "env": {}
        }
    }
}

if __name__ == "__main__":
    print("Anansi MCP Server Configuration")
    print("=" * 40)
    print()
    print("Add this to your Claude Code MCP config:")
    print()
    import json
    print(json.dumps(MCP_CONFIG, indent=2))
    print()
    print("Or run: claude mcp add anansi -- anansi-mcp")
    print()
    print("Example prompt to give Claude:")
    print(EXAMPLE_PROMPT)
