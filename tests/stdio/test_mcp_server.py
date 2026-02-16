"""
Tests for the modular MCP server (src.tv_mcp.mcp) using REAL data for integration.
"""

import asyncio
import os
from typing import Any
import pytest

from src.tv_mcp.mcp.serializers import serialize_error, serialize_success, toon_encode
from src.tv_mcp.mcp.server import mcp

# ── helpers ───────────────────────────────────────────────────────

def _run(coro: Any) -> Any:
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ── Tool registration ─────────────────────────────────────────────

EXPECTED_TOOLS = [
    "get_historical_data",
    "get_news_headlines",
    "get_news_content",
    "get_all_indicators",
    "get_ideas",
    "get_minds",
    "get_option_chain_greeks",
]

class TestToolRegistration:
    def test_all_tools_registered(self) -> None:
        registered = list(mcp._tool_manager._tools.keys())
        for name in EXPECTED_TOOLS:
            assert name in registered, f"Tool '{name}' not registered"

    def test_exactly_seven_tools(self) -> None:
        assert len(mcp._tool_manager._tools) == 7

# ── Tool handler integration (REAL DATA) ─────────────────────────

@pytest.mark.skipif(not os.getenv("TRADINGVIEW_COOKIE"), reason="TRADINGVIEW_COOKIE not set")
class TestToolHandlerIntegration:
    """Verify tool handlers produce valid real responses."""

    def test_get_historical_data_real(self) -> None:
        from src.tv_mcp.mcp.tools.historical import get_historical_data
        result = _run(get_historical_data(exchange="BINANCE", symbol="BTCUSDT", timeframe="1h", numb_price_candles=2))
        assert "success: true" in result.lower()
        assert "data" in result.lower()

    def test_get_all_indicators_real(self) -> None:
        from src.tv_mcp.mcp.tools.technicals import get_all_indicators
        result = _run(get_all_indicators(symbol="NIFTY", exchange="NSE"))
        assert "success: true" in result.lower()
        assert "RSI" in result

    def test_get_news_headlines_real(self) -> None:
        from src.tv_mcp.mcp.tools.news import get_news_headlines
        result = _run(get_news_headlines(symbol="AAPL", exchange="NASDAQ"))
        assert "headlines" in result.lower()

    def test_get_ideas_real(self) -> None:
        from src.tv_mcp.mcp.tools.social import get_ideas
        result = _run(get_ideas(symbol="BTCUSD", exchange="BITSTAMP"))
        assert "ideas" in result.lower()

    def test_get_minds_real(self) -> None:
        from src.tv_mcp.mcp.tools.social import get_minds
        result = _run(get_minds(symbol="TSLA", exchange="NASDAQ", limit=2))
        assert "data" in result.lower() or "text" in result.lower()

    def test_get_option_chain_greeks_real(self) -> None:
        from src.tv_mcp.mcp.tools.options import get_option_chain_greeks
        result = _run(get_option_chain_greeks(symbol="NIFTY", exchange="NSE"))
        assert "success: true" in result.lower()
