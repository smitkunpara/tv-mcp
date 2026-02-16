"""
Integration tests for minds service using real data.
"""

import pytest
import os
from src.tv_mcp.services.minds import fetch_minds

pytestmark = pytest.mark.skipif(
    not os.getenv("TRADINGVIEW_COOKIE"),
    reason="TRADINGVIEW_COOKIE not set"
)

class TestMindsIntegration:
    def test_fetch_real_minds(self):
        result = fetch_minds(symbol="TSLA", exchange="NASDAQ", limit=5)
        assert result["success"] is True
        assert len(result["data"]) > 0
        assert "text" in result["data"][0]
