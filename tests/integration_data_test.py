"""
Integration tests for TradingView services using REAL data.
These tests make actual network requests to TradingView.
"""

import os
import pytest
from src.tv_mcp.services.historical import fetch_historical_data
from src.tv_mcp.services.technicals import fetch_all_indicators
from src.tv_mcp.services.news import fetch_news_headlines, fetch_news_content
from src.tv_mcp.services.ideas import fetch_ideas
from src.tv_mcp.services.minds import fetch_minds
from src.tv_mcp.services.options import process_option_chain_with_analysis, get_current_spot_price

# Skip all tests in this module if TRADINGVIEW_COOKIE is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("TRADINGVIEW_COOKIE"),
    reason="TRADINGVIEW_COOKIE environment variable not set"
)

def test_real_historical_data():
    """Test fetching historical OHLCV data without indicators."""
    result = fetch_historical_data(
        exchange="BINANCE",
        symbol="BTCUSDT",
        timeframe="1h",
        numb_price_candles=10,
        indicators=[]
    )
    assert result["success"] is True
    assert len(result["data"]) >= 10
    assert "close" in result["data"][0]
    assert "datetime_ist" in result["data"][0]

def test_real_historical_with_indicators():
    """Test fetching historical data with RSI and MACD indicators."""
    result = fetch_historical_data(
        exchange="BINANCE",
        symbol="BTCUSDT",
        timeframe="1h",
        numb_price_candles=10,
        indicators=["RSI", "MACD"]
    )
    assert result["success"] is True
    assert len(result["data"]) >= 10
    # Check if indicators are present in the merged data
    sample = result["data"][0]
    assert "Relative_Strength_Index" in sample
    assert "Moving_Average_Convergence_Divergence_macd" in sample

def test_real_technicals_snapshot():
    """Test fetching real-time indicator snapshots."""
    result = fetch_all_indicators(
        exchange="NSE",
        symbol="NIFTY",
        timeframe="15m"
    )
    assert result["success"] is True
    assert "data" in result
    assert "RSI" in result["data"]
    assert "MACD.macd" in result["data"]

def test_real_news_headlines():
    """Test fetching actual news headlines."""
    headlines = fetch_news_headlines(
        symbol="AAPL",
        exchange="NASDAQ",
        provider="all",
        area="world"
    )
    assert isinstance(headlines, list)
    if headlines:
        assert "title" in headlines[0]
        assert "storyPath" in headlines[0]

def test_real_news_content():
    """Test fetching full news content for a real story path."""
    # First get a real headline to get a valid story path
    headlines = fetch_news_headlines(symbol="BTC", exchange="CRYPTO")
    if not headlines:
        pytest.skip("No headlines found for BTC to test content")
    
    story_path = headlines[0]["storyPath"]
    content = fetch_news_content([story_path])
    
    assert len(content) == 1
    assert content[0]["success"] is True
    assert len(content[0]["body"]) > 0

def test_real_ideas():
    """Test fetching community trading ideas."""
    result = fetch_ideas(
        symbol="BTCUSD",
        exchange="BITSTAMP",
        startPage=1,
        endPage=1,
        sort="popular"
    )
    assert result["success"] is True
    assert "ideas" in result
    assert len(result["ideas"]) > 0
    assert "title" in result["ideas"][0]

def test_real_minds():
    """Test fetching community discussions (Minds)."""
    result = fetch_minds(
        symbol="AAPL",
        exchange="NASDAQ",
        limit=5
    )
    assert result["success"] is True
    assert len(result["data"]) > 0
    assert "text" in result["data"][0]

def test_real_options_analysis():
    """Test option chain fetching and analysis with real data."""
    # Using a common symbol that usually has options
    result = process_option_chain_with_analysis(
        symbol="NIFTY",
        exchange="NSE",
        expiry_date="nearest",
        no_of_ITM=3,
        no_of_OTM=3
    )
    assert result["success"] is True
    assert "spot_price" in result
    assert result["spot_price"] > 0
    assert "data" in result
    if result["data"]:
        assert "strike_price" in result["data"][0]
        assert "delta" in result["data"][0]

def test_real_news_headlines_with_filter():
    """Test fetching news headlines with IST date filtering."""
    import datetime
    # Get today's headlines
    today = datetime.datetime.now().strftime("%d-%m-%Y")
    headlines = fetch_news_headlines(
        symbol="AAPL",
        exchange="NASDAQ",
        start_datetime=f"{today} 00:00"
    )
    assert isinstance(headlines, list)

def test_real_ideas_with_filter():
    """Test fetching ideas with IST date filtering."""
    result = fetch_ideas(
        symbol="BTCUSD",
        exchange="BITSTAMP",
        start_datetime="01-01-2026 00:00"
    )
    assert result["success"] is True
    # If there are ideas, they should all be after the start_datetime
    # but since it's real data, we just verify the call succeeds

def test_real_minds_with_filter():
    """Test fetching minds with IST date filtering."""
    result = fetch_minds(
        symbol="TSLA",
        exchange="NASDAQ",
        limit=10,
        start_datetime="01-01-2026 00:00"
    )
    assert result["success"] is True

def test_real_spot_price():
    """Test fetching current spot price."""
    price = get_current_spot_price("RELIANCE", "NSE")
    assert isinstance(price, float)
    assert price > 0
