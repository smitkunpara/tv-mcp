"""
FastMCP app factory and tool registration.

Creates the ``mcp`` FastMCP instance, registers all domain tools,
and exposes a ``main()`` entry-point.
"""

from fastmcp import FastMCP

from .tools.historical import get_historical_data
from .tools.news import get_news_content, get_news_headlines
from .tools.options import get_option_chain_greeks
from .tools.social import get_ideas, get_minds
from .tools.technicals import get_all_indicators

# ── FastMCP instance ─────────────────────────────────────────────
mcp = FastMCP("TradingView-MCP")

# ── Register tools ───────────────────────────────────────────────
mcp.tool()(get_historical_data)
mcp.tool()(get_news_headlines)
mcp.tool()(get_news_content)
mcp.tool()(get_all_indicators)
mcp.tool()(get_ideas)
mcp.tool()(get_minds)
mcp.tool()(get_option_chain_greeks)


def main() -> None:
    """Run the MCP server."""
    mcp.run()
