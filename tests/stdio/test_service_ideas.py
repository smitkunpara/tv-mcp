"""
Integration tests for ideas service using real data.
"""

import pytest
import os
from tv_mcp.services.ideas import fetch_ideas

pytestmark = pytest.mark.skipif(
    not os.getenv("TRADINGVIEW_COOKIE"),
    reason="TRADINGVIEW_COOKIE not set"
)

class TestIdeasIntegration:
    def test_fetch_real_ideas(self):
        result = fetch_ideas(symbol="BTCUSD", exchange="BITSTAMP")
        assert result["success"] is True
        assert len(result["ideas"]) > 0
        assert "title" in result["ideas"][0]
