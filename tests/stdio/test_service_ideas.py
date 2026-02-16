"""
Unit tests for src.tv_mcp.services.ideas.fetch_ideas.

All external calls (Ideas scraper) are mocked — no network access.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.tv_mcp.services.ideas import fetch_ideas
from src.tv_mcp.core.validators import ValidationError


# ── Validation tests ───────────────────────────────────────────────


class TestIdeasValidation:
    """Input validation must raise ValidationError for bad arguments."""

    def test_empty_symbol_raises(self):
        with pytest.raises(ValidationError, match="Symbol is required"):
            fetch_ideas(symbol="")

    def test_startPage_string_coercion(self):
        """String '2' should be coerced to int 2 without error."""
        with patch("src.tv_mcp.services.ideas.Ideas") as mock_cls:
            instance = MagicMock()
            mock_cls.return_value = instance
            instance.scrape.return_value = {
                "status": "success",
                "data": [{"title": "Idea 1", "timestamp": 1700000000}],
                "metadata": {},
                "error": None,
            }

            result = fetch_ideas(symbol="AAPL", exchange="NASDAQ", startPage=int("2"), endPage=int("3"))
            assert result["success"] is True

    def test_startPage_invalid_string_raises(self):
        with pytest.raises(ValidationError, match="startPage must be a valid integer"):
            fetch_ideas(symbol="AAPL", startPage=object())  # type: ignore[arg-type]

    def test_endPage_invalid_string_raises(self):
        with pytest.raises(ValidationError, match="endPage must be a valid integer"):
            fetch_ideas(symbol="AAPL", endPage=object())  # type: ignore[arg-type]

    def test_endPage_less_than_startPage_raises(self):
        with pytest.raises(ValidationError, match="endPage must be greater"):
            fetch_ideas(symbol="AAPL", startPage=5, endPage=3)

    def test_invalid_sort_raises(self):
        with pytest.raises(ValidationError, match="sort must be"):
            fetch_ideas(symbol="AAPL", sort="trending")


# ── Successful scrape ─────────────────────────────────────────────


class TestIdeasSuccess:
    """Successful scrape returns success=True with ideas list."""

    @patch("src.tv_mcp.services.ideas.Ideas")
    def test_returns_ideas(self, mock_ideas_cls):
        instance = MagicMock()
        mock_ideas_cls.return_value = instance
        fake_ideas = [
            {"title": "Bullish on AAPL", "timestamp": 1700000000, "author": "user1"},
            {"title": "Bear case", "timestamp": 1700100000, "author": "user2"},
        ]
        instance.scrape.return_value = {
            "status": "success",
            "data": fake_ideas,
            "metadata": {},
            "error": None,
        }

        result = fetch_ideas(symbol="AAPL", exchange="NASDAQ", sort="popular")

        assert result["success"] is True
        assert result["count"] == 2
        assert result["ideas"] == fake_ideas


# ── Date filtering ────────────────────────────────────────────────


class TestIdeasDateFiltering:
    """Timestamp-based date filtering on ideas."""

    @patch("src.tv_mcp.services.ideas.Ideas")
    def test_start_filter_excludes_old(self, mock_ideas_cls):
        instance = MagicMock()
        mock_ideas_cls.return_value = instance
        instance.scrape.return_value = {
            "status": "success",
            "data": [
                {"title": "Old idea", "timestamp": 1700000000},   # 2023-11-14
                {"title": "Recent idea", "timestamp": 1739000000}, # 2025-02-08
            ],
            "metadata": {},
            "error": None,
        }

        # Only after 01-01-2025 00:00 IST
        result = fetch_ideas(
            symbol="AAPL",
            exchange="NASDAQ",
            start_datetime="01-01-2025 00:00",
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["ideas"][0]["title"] == "Recent idea"


# ── Empty results ─────────────────────────────────────────────────


class TestIdeasEmpty:
    """Empty results return success=False with suggestion."""

    @patch("src.tv_mcp.services.ideas.Ideas")
    def test_empty_results(self, mock_ideas_cls):
        instance = MagicMock()
        mock_ideas_cls.return_value = instance
        instance.scrape.return_value = {
            "status": "success",
            "data": [],
            "metadata": {},
            "error": None,
        }

        result = fetch_ideas(symbol="OBSCURE_TICKER", exchange="BITSTAMP")

        assert result["success"] is False
        assert "suggestion" in result
