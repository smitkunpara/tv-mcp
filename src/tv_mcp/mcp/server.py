"""
FastMCP app factory and tool registration.

Creates the ``mcp`` FastMCP instance, registers all domain tools,
and exposes a ``main()`` entry-point.
"""

from fastmcp import FastMCP

from .tools.historical import get_historical_data
from .tools.news import get_news_content, get_news_headlines
from .tools.options import get_option_chain_greeks, get_nse_option_chain_oi
from .tools.social import get_ideas, get_minds
from .tools.technicals import get_all_indicators
from .tools.paper_trading import (
    place_order,
    close_position,
    view_positions,
    show_capital,
    set_alert,
    alert_manager,
    view_available_alerts,
    remove_alert,
)

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
mcp.tool()(get_nse_option_chain_oi)

# ── Paper Trading tools ──────────────────────────────────────────
mcp.tool()(place_order)
mcp.tool()(close_position)
mcp.tool()(view_positions)
mcp.tool()(show_capital)
mcp.tool()(set_alert)
mcp.tool()(alert_manager)
mcp.tool()(view_available_alerts)
mcp.tool()(remove_alert)


def main() -> None:
    """Run the MCP server."""
    mcp.run()
