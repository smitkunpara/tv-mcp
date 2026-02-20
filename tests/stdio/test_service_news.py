"""
Integration tests for news service using real data.
"""

import pytest
import os
from src.tv_mcp.services.news import fetch_news_headlines, fetch_news_content

pytestmark = pytest.mark.skipif(
    not os.getenv("TRADINGVIEW_COOKIE"),
    reason="TRADINGVIEW_COOKIE not set"
)

class TestNewsIntegration:
    def test_fetch_real_headlines(self):
        headlines = fetch_news_headlines(symbol="AAPL", exchange="NASDAQ")
        assert isinstance(headlines, list)
        if headlines:
            assert "title" in headlines[0]
            assert "id" in headlines[0]
            assert "storyPath" not in headlines[0]

    def test_fetch_real_content(self):
        headlines = fetch_news_headlines(symbol="BTCUSD", exchange="BITSTAMP")
        if not headlines:
            pytest.skip("No headlines found for BTCUSD")
        
        sid = headlines[0]["id"]
        content = fetch_news_content([sid])
        assert len(content) == 1
        assert content[0]["success"] is True
        assert len(content[0]["body"]) > 0
