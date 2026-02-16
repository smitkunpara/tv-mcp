"""
Unit tests for src.tv_mcp.services.news (fetch_news_headlines, fetch_news_content).

All external calls (News scraper) are mocked — no network access.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.tv_mcp.services.news import fetch_news_headlines, fetch_news_content
from src.tv_mcp.core.validators import ValidationError


# ── fetch_news_headlines validation ────────────────────────────────


class TestNewsHeadlinesValidation:
    """Input validation for fetch_news_headlines."""

    def test_empty_symbol_raises(self):
        with pytest.raises(ValidationError, match="Symbol is required"):
            fetch_news_headlines(symbol="")

    def test_invalid_datetime_format_start(self):
        with pytest.raises(ValidationError, match="Invalid start_datetime"):
            fetch_news_headlines(symbol="RELIANCE", start_datetime="2026/02/01 09:00")

    def test_invalid_datetime_format_end(self):
        with pytest.raises(ValidationError, match="Invalid end_datetime"):
            fetch_news_headlines(symbol="RELIANCE", end_datetime="not-a-date")


# ── fetch_news_headlines success ──────────────────────────────────


class TestNewsHeadlinesSuccess:
    """Successful headline scrape returns list of headline dicts."""

    @patch("src.tv_mcp.services.news.News")
    def test_returns_headline_list(self, mock_news_cls):
        instance = MagicMock()
        mock_news_cls.return_value = instance
        instance.scrape_headlines.return_value = {
            "status": "success",
            "data": [
                {"title": "Headline A", "published": 1707600000, "storyPath": "/news/a"},
                {"title": "Headline B", "published": 1707700000, "storyPath": "/news/b"},
            ],
            "metadata": {},
            "error": None,
        }

        result = fetch_news_headlines(symbol="RELIANCE")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["title"] == "Headline A"
        assert result[1]["storyPath"] == "/news/b"


# ── Date filtering ────────────────────────────────────────────────


class TestNewsHeadlinesDateFiltering:
    """Start/end datetime params filter headlines by timestamp."""

    @patch("src.tv_mcp.services.news.News")
    def test_start_filter_excludes_old(self, mock_news_cls):
        instance = MagicMock()
        mock_news_cls.return_value = instance
        # ts 1707600000 ≈ 2024-02-11 UTC
        # ts 1739000000 ≈ 2025-02-08 UTC
        instance.scrape_headlines.return_value = {
            "status": "success",
            "data": [
                {"title": "Old", "published": 1707600000, "storyPath": "/news/old"},
                {"title": "New", "published": 1739000000, "storyPath": "/news/new"},
            ],
            "metadata": {},
            "error": None,
        }

        # Filter: only after 01-01-2025 00:00 IST → ts ~1735669800
        result = fetch_news_headlines(
            symbol="RELIANCE",
            start_datetime="01-01-2025 00:00",
        )

        assert len(result) == 1
        assert result[0]["title"] == "New"

    @patch("src.tv_mcp.services.news.News")
    def test_end_filter_excludes_future(self, mock_news_cls):
        instance = MagicMock()
        mock_news_cls.return_value = instance
        instance.scrape_headlines.return_value = {
            "status": "success",
            "data": [
                {"title": "Old", "published": 1707600000, "storyPath": "/news/old"},
                {"title": "New", "published": 1739000000, "storyPath": "/news/new"},
            ],
            "metadata": {},
            "error": None,
        }

        # Filter: only before 01-01-2025 00:00 IST
        result = fetch_news_headlines(
            symbol="RELIANCE",
            end_datetime="01-01-2025 00:00",
        )

        assert len(result) == 1
        assert result[0]["title"] == "Old"


# ── fetch_news_content ────────────────────────────────────────────


class TestNewsContent:
    """fetch_news_content returns array of content results."""

    @patch("src.tv_mcp.services.news.News")
    def test_returns_content_array(self, mock_news_cls):
        instance = MagicMock()
        mock_news_cls.return_value = instance
        instance.scrape_content.return_value = {
            "status": "success",
            "data": {
                "title": "Breaking News",
                "body": [
                    {"type": "text", "content": "First paragraph."},
                    {"type": "text", "content": "Second paragraph."},
                ],
            },
            "metadata": {},
            "error": None,
        }

        result = fetch_news_content(["/news/story-1"])

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["success"] is True
        assert result[0]["title"] == "Breaking News"
        assert "First paragraph" in result[0]["body"]

    @patch("src.tv_mcp.services.news.News")
    def test_handles_per_story_errors(self, mock_news_cls):
        instance = MagicMock()
        mock_news_cls.return_value = instance
        instance.scrape_content.side_effect = [
            RuntimeError("404 Not Found"),
            {
                "status": "success",
                "data": {"title": "OK Story", "body": []},
                "metadata": {},
                "error": None,
            },
        ]

        result = fetch_news_content(["/news/bad", "/news/good"])

        assert len(result) == 2
        assert result[0]["success"] is False
        assert "Failed" in result[0]["error"]
        assert result[1]["success"] is True


# ── story_paths validation ────────────────────────────────────────


class TestNewsContentValidation:
    """Story paths must be valid."""

    def test_empty_story_paths_raises(self):
        with pytest.raises(ValidationError, match="At least one story path"):
            fetch_news_content([])

    def test_invalid_story_path_format(self):
        with pytest.raises(ValidationError, match="must start with '/news/'"):
            fetch_news_content(["/articles/bad-path"])
