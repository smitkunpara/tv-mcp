"""
Integration tests for historical service using real data.
"""

import pytest
import os
from tv_mcp.services.historical import fetch_historical_data
from tv_mcp.core.validators import ValidationError

# Skip if no cookie
pytestmark = pytest.mark.skipif(
    not os.getenv("TRADINGVIEW_COOKIE"),
    reason="TRADINGVIEW_COOKIE not set"
)

class TestHistoricalIntegration:
    def test_fetch_real_ohlcv(self):
        result = fetch_historical_data(
            exchange="BINANCE",
            symbol="BTCUSDT",
            timeframe="1h",
            numb_price_candles=5,
            indicators=[]
        )
        assert result["success"] is True
        assert len(result["data"]) == 5
        assert "close" in result["data"][0]

    def test_fetch_with_real_indicators(self):
        result = fetch_historical_data(
            exchange="NASDAQ",
            symbol="AAPL",
            timeframe="1d",
            numb_price_candles=5,
            indicators=["RSI", "MACD"]
        )
        assert result["success"] is True
        assert len(result["data"]) == 5
        assert "Relative_Strength_Index" in result["data"][0]

    def test_invalid_symbol_real_request(self):
        # Even with real requests, validation might catch it first
        with pytest.raises(ValidationError):
            fetch_historical_data("NSE", "", "1d", 10, [])

    def test_invalid_exchange_real_request(self):
        with pytest.raises(ValidationError):
            fetch_historical_data("INVALID_EX", "AAPL", "1d", 10, [])
