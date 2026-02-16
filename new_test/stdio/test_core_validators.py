"""
Parity tests: tv_scrapper.core.validators vs legacy tradingview_mcp.validators.

Ensures the new validator module produces identical results to the legacy one.
"""

import pytest

# New module
from src.tv_scrapper.core.validators import (
    VALID_EXCHANGES,
    VALID_TIMEFRAMES,
    VALID_NEWS_PROVIDERS,
    VALID_AREAS,
    INDICATOR_MAPPING,
    INDICATOR_FIELD_MAPPING,
    VALID_INDICATORS,
    ValidationError as NewValidationError,
    validate_exchange as new_validate_exchange,
    validate_timeframe as new_validate_timeframe,
    validate_news_provider as new_validate_news_provider,
    validate_area as new_validate_area,
    validate_indicators as new_validate_indicators,
    validate_symbol as new_validate_symbol,
    validate_story_paths as new_validate_story_paths,
)

# Legacy module
from src.tradingview_mcp.validators import (
    VALID_EXCHANGES as OLD_VALID_EXCHANGES,
    VALID_TIMEFRAMES as OLD_VALID_TIMEFRAMES,
    VALID_NEWS_PROVIDERS as OLD_VALID_NEWS_PROVIDERS,
    VALID_AREAS as OLD_VALID_AREAS,
    INDICATOR_MAPPING as OLD_INDICATOR_MAPPING,
    INDICATOR_FIELD_MAPPING as OLD_INDICATOR_FIELD_MAPPING,
    VALID_INDICATORS as OLD_VALID_INDICATORS,
    ValidationError as OldValidationError,
    validate_exchange as old_validate_exchange,
    validate_timeframe as old_validate_timeframe,
    validate_news_provider as old_validate_news_provider,
    validate_area as old_validate_area,
    validate_indicators as old_validate_indicators,
    validate_symbol as old_validate_symbol,
    validate_story_paths as old_validate_story_paths,
)


class TestConstantParity:
    """Constants must be identical between old and new modules."""

    def test_exchanges_equal(self):
        assert VALID_EXCHANGES == OLD_VALID_EXCHANGES

    def test_timeframes_equal(self):
        assert VALID_TIMEFRAMES == OLD_VALID_TIMEFRAMES

    def test_providers_equal(self):
        assert VALID_NEWS_PROVIDERS == OLD_VALID_NEWS_PROVIDERS

    def test_areas_equal(self):
        assert VALID_AREAS == OLD_VALID_AREAS

    def test_indicator_mapping_equal(self):
        assert INDICATOR_MAPPING == OLD_INDICATOR_MAPPING

    def test_indicator_field_mapping_equal(self):
        assert INDICATOR_FIELD_MAPPING == OLD_INDICATOR_FIELD_MAPPING

    def test_valid_indicators_equal(self):
        assert VALID_INDICATORS == OLD_VALID_INDICATORS


class TestValidatorFunctionParity:
    """Validator functions must behave identically for the same inputs."""

    # ── validate_exchange ──
    def test_exchange_valid(self):
        assert new_validate_exchange("nse") == old_validate_exchange("nse")

    def test_exchange_invalid(self):
        with pytest.raises(NewValidationError):
            new_validate_exchange("INVALID_EXCHANGE")
        with pytest.raises(OldValidationError):
            old_validate_exchange("INVALID_EXCHANGE")

    # ── validate_timeframe ──
    def test_timeframe_valid(self):
        assert new_validate_timeframe("1d") == old_validate_timeframe("1d")

    def test_timeframe_invalid(self):
        with pytest.raises(NewValidationError):
            new_validate_timeframe("3m")
        with pytest.raises(OldValidationError):
            old_validate_timeframe("3m")

    # ── validate_news_provider ──
    def test_provider_all(self):
        assert new_validate_news_provider("all") == old_validate_news_provider("all")

    def test_provider_specific(self):
        assert new_validate_news_provider("coindesk") == old_validate_news_provider("coindesk")

    def test_provider_invalid(self):
        with pytest.raises(NewValidationError):
            new_validate_news_provider("fake_provider")
        with pytest.raises(OldValidationError):
            old_validate_news_provider("fake_provider")

    # ── validate_area ──
    def test_area_valid(self):
        assert new_validate_area("asia") == old_validate_area("asia")

    def test_area_invalid(self):
        with pytest.raises(NewValidationError):
            new_validate_area("mars")
        with pytest.raises(OldValidationError):
            old_validate_area("mars")

    # ── validate_indicators ──
    def test_indicators_valid(self):
        new_result = new_validate_indicators(["RSI", "MACD"])
        old_result = old_validate_indicators(["RSI", "MACD"])
        assert new_result == old_result

    def test_indicators_with_invalid(self):
        new_ids, new_vers, new_errors, new_warnings = new_validate_indicators(["RSI", "FAKE"])
        old_ids, old_vers, old_errors, old_warnings = old_validate_indicators(["RSI", "FAKE"])
        assert new_ids == old_ids
        assert new_vers == old_vers
        assert len(new_errors) == len(old_errors)

    # ── validate_symbol ──
    def test_symbol_valid(self):
        assert new_validate_symbol("NIFTY") == old_validate_symbol("NIFTY")

    def test_symbol_empty(self):
        with pytest.raises(NewValidationError):
            new_validate_symbol("")
        with pytest.raises(OldValidationError):
            old_validate_symbol("")

    # ── validate_story_paths ──
    def test_story_paths_valid(self):
        paths = ["/news/article-1", "/news/article-2"]
        assert new_validate_story_paths(paths) == old_validate_story_paths(paths)

    def test_story_paths_empty(self):
        with pytest.raises(NewValidationError):
            new_validate_story_paths([])
        with pytest.raises(OldValidationError):
            old_validate_story_paths([])
