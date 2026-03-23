"""
FastMCP app factory and tool registration.

Creates the ``mcp`` FastMCP instance, registers all domain tools,
and exposes a ``main()`` entry-point.
"""

import os
import sys
import logging
from pathlib import Path
from fastmcp import FastMCP
from .tools.historical import get_historical_data
from .tools.news import get_news_content, get_news_headlines
from .tools.options import get_option_chain_greeks, get_nse_option_chain_oi
from .tools.social import get_ideas, get_minds
from .tools.technicals import get_all_indicators
from .tools.meta import (
    list_available_exchanges,
    list_supported_indicators,
    list_available_timeframes,
)
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

# ── Logging Setup ────────────────────────────────────────────────
def _setup_logging():
    is_debug = os.environ.get("DEBUG", "").lower() in ("true", "1", "t", "yes", "y")
    if is_debug:
        # Place log file in the same directory as this server.py file
        log_file_path = Path(__file__).resolve().parent / "server.log"
        
        # Configure logging to write to file ONLY, no console output
        # to prevent corrupting the stdio MCP protocol communication
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            handlers=[
                logging.FileHandler(log_file_path, encoding="utf-8")
            ],
            force=True  # Override any existing logging configuration
        )
        
        logger = logging.getLogger(__name__)
        logger.debug("==================================================")
        logger.debug("TradingView MCP Server initialized in DEBUG mode")
        logger.debug("Log file path: %s", log_file_path)
        logger.debug("==================================================")
        
        # Also capture uncaught exceptions in the log
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
            
        sys.excepthook = handle_exception
        
    else:
        # When not in debug mode, suppress all logging to prevent stdout corruption
        logging.getLogger().addHandler(logging.NullHandler())

_setup_logging()
logger = logging.getLogger(__name__)

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

# ── Metadata tools ───────────────────────────────────────────────
mcp.tool()(list_available_exchanges)
mcp.tool()(list_supported_indicators)
mcp.tool()(list_available_timeframes)

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
