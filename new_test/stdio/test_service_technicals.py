"""
Unit tests for src.tv_mcp.services.technicals.fetch_all_indicators.

All external calls (Technicals) are mocked — no network access.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.tv_mcp.services.technicals import fetch_all_indicators
from src.tv_mcp.core.validators import ValidationError


# ── Validation tests ───────────────────────────────────────────────


class TestTechnicalsValidation:
    """Input validation must raise ValidationError for bad arguments."""

    def test_invalid_exchange_raises(self):
        with pytest.raises(ValidationError, match="Invalid exchange"):
            fetch_all_indicators("BAD_EX", "AAPL", "1d")

    def test_empty_symbol_raises(self):
        with pytest.raises(ValidationError, match="Symbol is required"):
            fetch_all_indicators("NSE", "", "1d")

    def test_invalid_timeframe_raises(self):
        with pytest.raises(ValidationError, match="Invalid timeframe"):
            fetch_all_indicators("NSE", "RELIANCE", "7m")


# ── Successful scrape ─────────────────────────────────────────────


class TestTechnicalsSuccess:
    """Successful scrape returns success=True with data."""

    @patch("src.tv_mcp.services.technicals.Technicals")
    def test_successful_scrape(self, mock_technicals_cls):
        instance = MagicMock()
        mock_technicals_cls.return_value = instance
        instance.scrape.return_value = {
            "status": "success",
            "data": {
                "RSI": 65.4,
                "MACD": {"macd": 1.2, "signal": 0.8, "histogram": 0.4},
            },
        }

        result = fetch_all_indicators("NSE", "RELIANCE", "1d")

        assert result["success"] is True
        assert result["data"]["RSI"] == 65.4
        instance.scrape.assert_called_once_with(
            symbol="RELIANCE",
            exchange="NSE",
            timeframe="1d",
            allIndicators=True,
        )


# ── Unexpected return format ──────────────────────────────────────


class TestTechnicalsUnexpectedFormat:
    """Unexpected response format returns success=False."""

    @patch("src.tv_mcp.services.technicals.Technicals")
    def test_unexpected_format_list(self, mock_technicals_cls):
        instance = MagicMock()
        mock_technicals_cls.return_value = instance
        instance.scrape.return_value = [1, 2, 3]  # not a dict with status

        result = fetch_all_indicators("NSE", "RELIANCE", "1d")

        assert result["success"] is False
        assert "Unexpected response" in result["message"]

    @patch("src.tv_mcp.services.technicals.Technicals")
    def test_unexpected_format_dict_no_status(self, mock_technicals_cls):
        instance = MagicMock()
        mock_technicals_cls.return_value = instance
        instance.scrape.return_value = {"something": "else"}

        result = fetch_all_indicators("NSE", "RELIANCE", "1d")

        assert result["success"] is False


# ── Exception handling ────────────────────────────────────────────


class TestTechnicalsExceptionHandling:
    """Scraper exceptions return success=False gracefully."""

    @patch("src.tv_mcp.services.technicals.Technicals")
    def test_scrape_exception(self, mock_technicals_cls):
        instance = MagicMock()
        mock_technicals_cls.return_value = instance
        instance.scrape.side_effect = RuntimeError("Connection timeout")

        result = fetch_all_indicators("NSE", "RELIANCE", "1d")

        assert result["success"] is False
        assert "Failed to fetch indicators" in result["message"]
