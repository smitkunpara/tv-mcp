
import pytest
from unittest.mock import MagicMock, patch
from tv_mcp.services.historical import fetch_historical_data

def test_fetch_historical_data_error_propagation():
    """Test that historical data service correctly propagates TradingView errors when using indicators."""
    
    # Mock settings and JWT token
    with patch("tv_mcp.core.settings.settings") as mock_settings, \
         patch("tv_mcp.services.historical.get_valid_jwt_token", return_value="fake_token"):
        
        mock_settings.TRADINGVIEW_COOKIE = "some_cookie"
        
        # Mock Streamer
        with patch("tv_mcp.services.historical.Streamer") as MockStreamer:
            mock_streamer_instance = MockStreamer.return_value
            
            # Simulated error response
            expected_error = "Symbol 'SENSEX' not found on exchange 'NSE'."
            error_response = {
                "status": "failed",
                "data": None,
                "metadata": {
                    "exchange": "NSE",
                    "symbol": "SENSEX"
                },
                "error": expected_error
            }
            
            mock_streamer_instance.get_candles.return_value = error_response
            
            # Call service with indicators (Case 2)
            result = fetch_historical_data(
                exchange="NSE",
                symbol="SENSEX",
                timeframe="1d",
                numb_price_candles=10,
                indicators=["RSI"]
            )
            
            # Verify result
            assert result["success"] is False
            assert expected_error in result["message"]
            assert expected_error in result["errors"]

def test_fetch_historical_data_partial_success():
    """Test that if at least one batch succeeds, we return data even if others fail."""
    
    with patch("tv_mcp.core.settings.settings") as mock_settings, \
         patch("tv_mcp.services.historical.get_valid_jwt_token", return_value="fake_token"):
        
        mock_settings.TRADINGVIEW_COOKIE = "some_cookie"
        
        with patch("tv_mcp.services.historical.Streamer") as MockStreamer:
            mock_streamer_instance = MockStreamer.return_value
            
            # Mock get_candles to succeed on first call, fail on second
            # BATCH_SIZE is 2
            success_data = {
                "ohlcv": [{"timestamp": 1000, "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000, "index": 0}],
                "indicators": {"STD;RSI": [{"timestamp": 1000, "value": 50}]}
            }
            
            # Simpler approach: return success for the first call, error for others
            mock_streamer_instance.get_candles.side_effect = [
                {"status": "success", "data": success_data},
                {"status": "failed", "error": "Batch failure"}
            ]
            
            result = fetch_historical_data(
                exchange="NSE",
                symbol="RELIANCE",
                timeframe="1d",
                numb_price_candles=1,
                indicators=["RSI", "MACD", "CCI"] # 3 indicators -> 2 batches
            )
            
            assert result["success"] is True
            assert len(result["data"]) > 0
            # Note: partial success still returns True because we have OHLC data
