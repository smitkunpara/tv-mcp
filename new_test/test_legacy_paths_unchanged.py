"""
Legacy import path stability tests.

Ensures that existing import paths from the old codebase continue to resolve
during the migration period. These are critical regression guards.
"""

import pytest


class TestLegacyPathsUnchanged:
    """Verify all legacy import paths still resolve."""

    def test_tradingview_mcp_init(self):
        from src.tradingview_mcp import __version__
        assert __version__ is not None

    def test_tradingview_mcp_config(self):
        from src.tradingview_mcp.config import settings, Settings
        assert settings is not None
        assert Settings is not None

    def test_tradingview_mcp_validators(self):
        from src.tradingview_mcp.validators import (
            ValidationError,
            VALID_EXCHANGES,
            VALID_TIMEFRAMES,
            validate_exchange,
            validate_timeframe,
            validate_symbol,
        )
        assert len(VALID_EXCHANGES) > 0
        assert len(VALID_TIMEFRAMES) > 0

    def test_tradingview_mcp_auth(self):
        from src.tradingview_mcp.auth import extract_jwt_token, get_token_info
        assert callable(extract_jwt_token)
        assert callable(get_token_info)

    def test_tradingview_mcp_utils(self):
        from src.tradingview_mcp.utils import (
            convert_timestamp_to_indian_time,
            merge_ohlc_with_indicators,
            extract_news_body,
        )
        assert callable(convert_timestamp_to_indian_time)

    def test_tradingview_mcp_tools(self):
        from src.tradingview_mcp.tradingview_tools import (
            fetch_historical_data,
            fetch_news_headlines,
            fetch_news_content,
            fetch_all_indicators,
            fetch_ideas,
            fetch_minds,
            process_option_chain_with_analysis,
        )
        assert callable(fetch_historical_data)
        assert callable(process_option_chain_with_analysis)

    def test_vercel_index_app(self):
        from vercel.index import app
        assert app is not None

    def test_vercel_models(self):
        from vercel.models import (
            HistoricalDataRequest,
            NewsHeadlinesRequest,
            OptionChainGreeksRequest,
        )
        assert HistoricalDataRequest is not None
