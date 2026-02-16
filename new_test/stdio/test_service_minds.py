"""
Unit tests for src.tv_mcp.services.minds.fetch_minds.

All external calls (Minds scraper) are mocked — no network access.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.tv_mcp.services.minds import fetch_minds
from src.tv_mcp.core.validators import ValidationError


# ── Validation tests ───────────────────────────────────────────────


class TestMindsValidation:
    """Input validation must raise ValidationError for bad arguments."""

    def test_invalid_exchange_raises(self):
        with pytest.raises(ValidationError, match="Invalid exchange"):
            fetch_minds(symbol="RELIANCE", exchange="BAD_EX")

    def test_empty_symbol_raises(self):
        with pytest.raises(ValidationError, match="Symbol is required"):
            fetch_minds(symbol="", exchange="NSE")

    def test_limit_string_coercion(self):
        """String '10' should be coerced to int 10 without error."""
        with patch("src.tv_mcp.services.minds.Minds") as mock_cls:
            instance = MagicMock()
            mock_cls.return_value = instance
            instance.get_minds.return_value = {
                "status": "ok",
                "data": [{"text": "Hello"}],
                "total": 1,
            }

            result = fetch_minds(symbol="RELIANCE", exchange="NSE", limit=int("10"))
            assert result["success"] is True

    def test_limit_zero_raises(self):
        with pytest.raises(ValidationError, match="positive integer"):
            fetch_minds(symbol="RELIANCE", exchange="NSE", limit=0)

    def test_limit_negative_raises(self):
        with pytest.raises(ValidationError, match="positive integer"):
            fetch_minds(symbol="RELIANCE", exchange="NSE", limit=-5)

    def test_limit_invalid_string_raises(self):
        with pytest.raises(ValidationError, match="valid positive integer"):
            fetch_minds(symbol="RELIANCE", exchange="NSE", limit=object())  # type: ignore[arg-type]


# ── Successful scrape ─────────────────────────────────────────────


class TestMindsSuccess:
    """Successful scrape returns success=True with discussion data."""

    @patch("src.tv_mcp.services.minds.Minds")
    def test_returns_discussions(self, mock_minds_cls):
        instance = MagicMock()
        mock_minds_cls.return_value = instance
        fake_response = {
            "status": "ok",
            "data": [
                {"text": "Bullish outlook", "timestamp": "2026-01-15T10:00:00"},
                {"text": "Watch the support", "timestamp": "2026-01-16T10:00:00"},
            ],
            "total": 2,
        }
        instance.get_minds.return_value = fake_response

        result = fetch_minds(symbol="RELIANCE", exchange="NSE")

        assert result["success"] is True
        assert result["total"] == 2
        assert len(result["data"]) == 2
        instance.get_minds.assert_called_once_with(symbol="NSE:RELIANCE", limit=None)


# ── Failed status from scraper ────────────────────────────────────


class TestMindsFailedStatus:
    """Failed status from the scraper returns success=False."""

    @patch("src.tv_mcp.services.minds.Minds")
    def test_failed_status(self, mock_minds_cls):
        instance = MagicMock()
        mock_minds_cls.return_value = instance
        instance.get_minds.return_value = {
            "status": "failed",
            "error": "Symbol not found",
        }

        result = fetch_minds(symbol="RELIANCE", exchange="NSE")

        assert result["success"] is False
        assert "Symbol not found" in result["message"]


# ── Exception handling ────────────────────────────────────────────


class TestMindsExceptionHandling:
    """Scraper exceptions return success=False gracefully."""

    @patch("src.tv_mcp.services.minds.Minds")
    def test_handles_exception(self, mock_minds_cls):
        instance = MagicMock()
        mock_minds_cls.return_value = instance
        instance.get_minds.side_effect = RuntimeError("Network error")

        result = fetch_minds(symbol="RELIANCE", exchange="NSE")

        assert result["success"] is False
        assert "Failed to fetch minds" in result["message"]
