"""
Integration tests for options service using real data.
"""

import pytest
import os
from src.tv_mcp.services.options import process_option_chain_with_analysis, get_current_spot_price

pytestmark = pytest.mark.skipif(
    not os.getenv("TRADINGVIEW_COOKIE"),
    reason="TRADINGVIEW_COOKIE not set"
)

class TestOptionsIntegration:
    def test_fetch_real_spot_price(self):
        price = get_current_spot_price("AAPL", "NASDAQ")
        assert isinstance(price, float)
        assert price > 0

    def test_fetch_real_option_chain(self):
        # NIFTY usually has plenty of options
        result = process_option_chain_with_analysis(
            symbol="NIFTY",
            exchange="NSE",
            expiry_date="nearest"
        )
        assert result["success"] is True
        assert result["spot_price"] > 0
        assert len(result["data"]) > 0
