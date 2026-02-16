"""
Integration tests for technicals service using real data.
"""

import pytest
import os
from src.tv_mcp.services.technicals import fetch_all_indicators

pytestmark = pytest.mark.skipif(
    not os.getenv("TRADINGVIEW_COOKIE"),
    reason="TRADINGVIEW_COOKIE not set"
)

class TestTechnicalsIntegration:
    def test_fetch_real_indicators(self):
        result = fetch_all_indicators(
            exchange="BINANCE",
            symbol="BTCUSDT",
            timeframe="1h"
        )
        assert result["success"] is True
        assert "RSI" in result["data"]
        assert "MACD.macd" in result["data"]

    def test_invalid_symbol_indicators(self):
        result = fetch_all_indicators(
            exchange="NASDAQ",
            symbol="NON_EXISTENT_SYMBOL_123",
            timeframe="1d"
        )
        # Should return success=False or an error message from API
        assert result["success"] is False or not result.get("data")
