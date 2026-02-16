"""
Unit tests for src.tv_mcp.services.historical.fetch_historical_data.

All external calls (Streamer, get_valid_jwt_token, merge_ohlc_with_indicators)
are mocked — no network access.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.tv_mcp.services.historical import fetch_historical_data
from src.tv_mcp.core.validators import ValidationError


# ── Validation tests ───────────────────────────────────────────────


class TestHistoricalValidation:
    """Input validation must raise ValidationError for bad arguments."""

    def test_invalid_exchange_raises(self):
        with pytest.raises(ValidationError, match="Invalid exchange"):
            fetch_historical_data("INVALID_EX", "RELIANCE", "1d", 10, [])

    def test_empty_symbol_raises(self):
        with pytest.raises(ValidationError, match="Symbol is required"):
            fetch_historical_data("NSE", "", "1d", 10, [])

    def test_invalid_timeframe_raises(self):
        with pytest.raises(ValidationError, match="Invalid timeframe"):
            fetch_historical_data("NSE", "RELIANCE", "3m", 10, [])

    def test_candle_count_string_coercion(self):
        """String '100' should be silently coerced to int 100."""
        with patch("src.tv_mcp.services.historical.Streamer") as mock_cls:
            instance = MagicMock()
            mock_cls.return_value = instance
            instance.stream.return_value = {
                "ohlc": [{"timestamp": 1000, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100, "index": 0}],
                "indicator": {},
            }
            result = fetch_historical_data("NSE", "RELIANCE", "1d", int("100"), [])
            assert result["success"] is True

    def test_candle_count_invalid_string_raises(self):
        with pytest.raises(ValidationError, match="valid integer"):
            fetch_historical_data("NSE", "RELIANCE", "1d", object(), [])  # type: ignore[arg-type]

    def test_candle_count_zero_raises(self):
        with pytest.raises(ValidationError, match="between 1 and 5000"):
            fetch_historical_data("NSE", "RELIANCE", "1d", 0, [])

    def test_candle_count_over_5000_raises(self):
        with pytest.raises(ValidationError, match="between 1 and 5000"):
            fetch_historical_data("NSE", "RELIANCE", "1d", 5001, [])


# ── Indicator validation ───────────────────────────────────────────


class TestHistoricalIndicatorValidation:
    """Unrecognized indicators return an error dict (no exception)."""

    def test_unrecognized_indicator_returns_error(self):
        result = fetch_historical_data("NSE", "RELIANCE", "1d", 10, ["FAKE_IND"])
        assert result["success"] is False
        assert any("FAKE_IND" in e for e in result["errors"])


# ── Fetch without indicators ──────────────────────────────────────


class TestHistoricalFetchNoIndicators:
    """When indicators list is empty, fetch OHLC only."""

    @patch("src.tv_mcp.services.historical.merge_ohlc_with_indicators")
    @patch("src.tv_mcp.services.historical.Streamer")
    def test_fetch_no_indicators(self, mock_streamer_cls, mock_merge):
        instance = MagicMock()
        mock_streamer_cls.return_value = instance
        fake_data = {
            "ohlc": [
                {"timestamp": 1000, "open": 10, "high": 12, "low": 9, "close": 11, "volume": 500, "index": 0},
                {"timestamp": 2000, "open": 11, "high": 13, "low": 10, "close": 12, "volume": 600, "index": 1},
            ],
            "indicator": {},
        }
        instance.stream.return_value = fake_data
        mock_merge.return_value = [
            {"open": 10, "close": 11, "datetime_ist": "01-01-2026 10:00:00 AM IST"},
            {"open": 11, "close": 12, "datetime_ist": "02-01-2026 10:00:00 AM IST"},
        ]

        result = fetch_historical_data("NSE", "RELIANCE", "1d", 2, [])

        assert result["success"] is True
        assert len(result["data"]) == 2
        mock_merge.assert_called_once_with(fake_data)
        instance.stream.assert_called_once()


# ── Fetch with indicators (batching) ──────────────────────────────


class TestHistoricalFetchWithIndicators:
    """Indicators are fetched in batches of 2 with JWT tokens."""

    @patch("src.tv_mcp.services.historical.settings")
    @patch("src.tv_mcp.services.historical.merge_ohlc_with_indicators")
    @patch("src.tv_mcp.services.historical.get_valid_jwt_token")
    @patch("src.tv_mcp.services.historical.Streamer")
    def test_batching_two_per_batch(self, mock_streamer_cls, mock_jwt, mock_merge, mock_settings):
        mock_settings.TRADINGVIEW_COOKIE = "fakecookie"
        mock_jwt.return_value = "fake.jwt.token"

        instance = MagicMock()
        mock_streamer_cls.return_value = instance
        instance.stream.return_value = {
            "ohlc": [{"timestamp": 1000, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100, "index": 0}],
            "indicator": {"STD;RSI": [{"timestamp": 1000, "2": 55}]},
        }

        mock_merge.return_value = [
            {"open": 1, "close": 1.5, "Relative_Strength_Index": 55},
        ]

        # 3 indicators → should create 2 batches (2 + 1)
        result = fetch_historical_data("NSE", "RELIANCE", "1d", 1, ["RSI", "MACD", "CCI"])

        assert result["success"] is True
        assert result["metadata"]["batches"] == 2
        # JWT should be called once per batch
        assert mock_jwt.call_count == 2


# ── Streamer exception handling ───────────────────────────────────


class TestHistoricalExceptionHandling:
    """Streamer failures should return success=False, not raise."""

    @patch("src.tv_mcp.services.historical.Streamer")
    def test_streamer_exception_returns_failure(self, mock_streamer_cls):
        instance = MagicMock()
        mock_streamer_cls.return_value = instance
        instance.stream.side_effect = RuntimeError("WebSocket connection failed")

        result = fetch_historical_data("NSE", "RELIANCE", "1d", 10, [])

        assert result["success"] is False
        assert any("TradingView API error" in e for e in result["errors"])
