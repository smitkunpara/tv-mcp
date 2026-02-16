"""
Tests for the modular MCP server (src.tv_mcp.mcp).

Covers:
  - Tool registration (all 7 tool names present)
  - Serializer functions (toon_encode, serialize_success, serialize_error)
  - Tool handlers delegate to correct service functions (mocked)
  - Error serialization format
"""

import asyncio
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.tv_mcp.mcp.serializers import serialize_error, serialize_success, toon_encode
from src.tv_mcp.mcp.server import mcp


# ── helpers ───────────────────────────────────────────────────────

def _run(coro: Any) -> Any:
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tool registration ─────────────────────────────────────────────


EXPECTED_TOOLS = [
    "get_historical_data",
    "get_news_headlines",
    "get_news_content",
    "get_all_indicators",
    "get_ideas",
    "get_minds",
    "get_option_chain_greeks",
]


class TestToolRegistration:
    """Verify all 7 tools are registered on the FastMCP instance."""

    def test_all_tools_registered(self) -> None:
        registered = list(mcp._tool_manager._tools.keys())
        for name in EXPECTED_TOOLS:
            assert name in registered, f"Tool '{name}' not registered"

    def test_exactly_seven_tools(self) -> None:
        assert len(mcp._tool_manager._tools) == 7

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_each_tool_present(self, tool_name: str) -> None:
        assert tool_name in mcp._tool_manager._tools


# ── Serializer functions ─────────────────────────────────────────


class TestSerializers:
    """Unit tests for toon_encode, serialize_success, serialize_error."""

    def test_toon_encode_dict(self) -> None:
        result = toon_encode({"key": "value"})
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result

    def test_toon_encode_list(self) -> None:
        result = toon_encode([1, 2, 3])
        assert isinstance(result, str)

    def test_serialize_success_returns_string(self) -> None:
        result = serialize_success({"success": True, "data": [1, 2]})
        assert isinstance(result, str)
        assert "success" in result

    def test_serialize_error_basic(self) -> None:
        result = serialize_error("something broke")
        assert isinstance(result, str)
        assert "something broke" in result
        assert "success" in result  # should contain success: false

    def test_serialize_error_with_details(self) -> None:
        result = serialize_error("bad input", details={"field": "exchange"})
        assert isinstance(result, str)
        assert "bad input" in result
        assert "exchange" in result

    def test_serialize_error_without_details(self) -> None:
        result = serialize_error("oops")
        assert isinstance(result, str)
        assert "oops" in result
        # No 'details' key when details is None
        assert "details" not in result


# ── Tool handler delegation ──────────────────────────────────────


class TestToolHandlerDelegation:
    """Verify each tool handler calls the correct service function."""

    @patch("src.tv_mcp.mcp.tools.historical.fetch_historical_data")
    def test_get_historical_data_delegates(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = {"success": True, "data": []}
        from src.tv_mcp.mcp.tools.historical import get_historical_data

        result = _run(
            get_historical_data(
                exchange="NSE",
                symbol="NIFTY",
                timeframe="1d",
                numb_price_candles=10,
                indicators=[],
            )
        )

        mock_fetch.assert_called_once_with(
            exchange="NSE",
            symbol="NIFTY",
            timeframe="1d",
            numb_price_candles=10,
            indicators=[],
        )
        assert isinstance(result, str)
        assert "success" in result

    @patch("src.tv_mcp.mcp.tools.news.fetch_news_headlines")
    def test_get_news_headlines_delegates(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{"title": "test headline"}]
        from src.tv_mcp.mcp.tools.news import get_news_headlines

        result = _run(get_news_headlines(symbol="AAPL"))

        mock_fetch.assert_called_once()
        assert isinstance(result, str)
        assert "test headline" in result

    @patch("src.tv_mcp.mcp.tools.news.fetch_news_content")
    def test_get_news_content_delegates(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{"success": True, "title": "Article", "body": "text"}]
        from src.tv_mcp.mcp.tools.news import get_news_content

        result = _run(get_news_content(story_paths=["/news/test-story"]))

        mock_fetch.assert_called_once_with(["/news/test-story"])
        assert isinstance(result, str)
        assert "Article" in result

    @patch("src.tv_mcp.mcp.tools.technicals.fetch_all_indicators")
    def test_get_all_indicators_delegates(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = {"success": True, "data": {"RSI": 55.0}}
        from src.tv_mcp.mcp.tools.technicals import get_all_indicators

        result = _run(get_all_indicators(symbol="NIFTY", exchange="NSE"))

        mock_fetch.assert_called_once_with(exchange="NSE", symbol="NIFTY", timeframe="1m")
        assert isinstance(result, str)
        assert "RSI" in result

    @patch("src.tv_mcp.mcp.tools.social.fetch_ideas")
    def test_get_ideas_delegates(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = {"success": True, "ideas": [], "count": 0}
        from src.tv_mcp.mcp.tools.social import get_ideas

        result = _run(get_ideas(symbol="AAPL"))

        mock_fetch.assert_called_once()
        assert isinstance(result, str)

    @patch("src.tv_mcp.mcp.tools.social.fetch_minds")
    def test_get_minds_delegates(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = {"success": True, "data": [], "total": 0}
        from src.tv_mcp.mcp.tools.social import get_minds

        result = _run(get_minds(symbol="NIFTY", exchange="NSE"))

        mock_fetch.assert_called_once()
        assert isinstance(result, str)

    @patch("src.tv_mcp.mcp.tools.options.process_option_chain_with_analysis")
    def test_get_option_chain_greeks_delegates(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = {"success": True, "data": [], "spot_price": 24500}
        from src.tv_mcp.mcp.tools.options import get_option_chain_greeks

        result = _run(
            get_option_chain_greeks(symbol="NIFTY", exchange="NSE")
        )

        mock_fetch.assert_called_once()
        assert isinstance(result, str)
        assert "24500" in result


# ── Error handling in tool handlers ──────────────────────────────


class TestToolHandlerErrors:
    """Verify tool handlers catch exceptions and serialize errors correctly."""

    @patch("src.tv_mcp.mcp.tools.historical.fetch_historical_data")
    def test_validation_error_is_serialized(self, mock_fetch: MagicMock) -> None:
        from src.tv_mcp.core.validators import ValidationError
        from src.tv_mcp.mcp.tools.historical import get_historical_data

        mock_fetch.side_effect = ValidationError("bad exchange")

        result = _run(
            get_historical_data(
                exchange="BAD",
                symbol="X",
                timeframe="1d",
                numb_price_candles=10,
            )
        )

        assert isinstance(result, str)
        assert "bad exchange" in result

    @patch("src.tv_mcp.mcp.tools.historical.fetch_historical_data")
    def test_unexpected_error_is_serialized(self, mock_fetch: MagicMock) -> None:
        from src.tv_mcp.mcp.tools.historical import get_historical_data

        mock_fetch.side_effect = RuntimeError("network down")

        result = _run(
            get_historical_data(
                exchange="NSE",
                symbol="NIFTY",
                timeframe="1d",
                numb_price_candles=10,
            )
        )

        assert isinstance(result, str)
        assert "Unexpected error" in result
        assert "network down" in result

    @patch("src.tv_mcp.mcp.tools.news.fetch_news_headlines")
    def test_news_headlines_error(self, mock_fetch: MagicMock) -> None:
        from src.tv_mcp.mcp.tools.news import get_news_headlines

        mock_fetch.side_effect = Exception("timeout")

        result = _run(get_news_headlines(symbol="AAPL"))

        assert isinstance(result, str)
        assert "timeout" in result

    @patch("src.tv_mcp.mcp.tools.social.fetch_ideas")
    def test_ideas_error(self, mock_fetch: MagicMock) -> None:
        from src.tv_mcp.mcp.tools.social import get_ideas

        mock_fetch.side_effect = Exception("scrape failed")

        result = _run(get_ideas(symbol="X"))

        assert isinstance(result, str)
        assert "scrape failed" in result

    def test_historical_candles_out_of_range(self) -> None:
        """numb_price_candles > 5000 should produce a validation error."""
        from src.tv_mcp.mcp.tools.historical import get_historical_data

        result = _run(
            get_historical_data(
                exchange="NSE",
                symbol="NIFTY",
                timeframe="1d",
                numb_price_candles=9999,
            )
        )

        assert isinstance(result, str)
        assert "numb_price_candles" in result


# ── __init__ exports ─────────────────────────────────────────────


class TestMCPPackageExports:
    """Verify the mcp package exports mcp and main."""

    def test_mcp_exported(self) -> None:
        from src.tv_mcp.mcp import mcp as exported_mcp

        assert exported_mcp is mcp

    def test_main_exported(self) -> None:
        from src.tv_mcp.mcp import main

        assert callable(main)
