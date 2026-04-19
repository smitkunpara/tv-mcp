"""
Tests for tv_mcp.core.validators — standalone validation tests.

Ensures all validator functions behave correctly.
"""

import pytest

from tv_mcp.core.validators import (
    VALID_EXCHANGES,
    VALID_TIMEFRAMES,
    VALID_NEWS_PROVIDERS,
    VALID_AREAS,
    INDICATOR_MAPPING,
    INDICATOR_FIELD_MAPPING,
    VALID_INDICATORS,
    ValidationError,
    validate_exchange,
    validate_timeframe,
    validate_news_provider,
    validate_area,
    validate_indicators,
    validate_symbol,
)


class TestConstants:
    """Constants must be defined and non-empty."""

    def test_exchanges_non_empty(self):
        assert len(VALID_EXCHANGES) > 0

    def test_timeframes_non_empty(self):
        assert len(VALID_TIMEFRAMES) > 0

    def test_providers_non_empty(self):
        assert len(VALID_NEWS_PROVIDERS) > 0

    def test_areas_non_empty(self):
        assert len(VALID_AREAS) > 0

    def test_indicator_mapping_non_empty(self):
        assert len(INDICATOR_MAPPING) > 0

    def test_indicator_field_mapping_non_empty(self):
        assert len(INDICATOR_FIELD_MAPPING) > 0

    def test_valid_indicators_non_empty(self):
        assert len(VALID_INDICATORS) > 0

    def test_exchanges_contain_common(self):
        lower = {e.lower() for e in VALID_EXCHANGES}
        assert "nse" in lower
        assert "nasdaq" in lower

    def test_timeframes_contain_common(self):
        assert "1d" in VALID_TIMEFRAMES
        assert "1h" in VALID_TIMEFRAMES


class TestValidatorFunctions:
    """Validator functions must work correctly for valid and invalid inputs."""

    # ── validate_exchange ──
    def test_exchange_valid(self):
        result = validate_exchange("nse")
        assert result.upper() == "NSE"

    def test_exchange_uppercase(self):
        result = validate_exchange("NASDAQ")
        assert result.upper() == "NASDAQ"

    def test_exchange_invalid(self):
        with pytest.raises(ValidationError):
            validate_exchange("INVALID_EXCHANGE")

    # ── validate_timeframe ──
    def test_timeframe_valid(self):
        result = validate_timeframe("1d")
        assert result == "1d"

    def test_timeframe_invalid(self):
        with pytest.raises(ValidationError):
            validate_timeframe("3m")

    # ── validate_news_provider ──
    def test_provider_all(self):
        result = validate_news_provider("all")
        # "all" maps to None (meaning no specific provider filter)
        assert result is None

    def test_provider_specific(self):
        result = validate_news_provider("tradingview")
        assert result is not None

    def test_provider_invalid(self):
        with pytest.raises(ValidationError):
            validate_news_provider("fake_provider")

    # ── validate_area ──
    def test_area_valid(self):
        result = validate_area("asia")
        assert result is not None

    def test_area_invalid(self):
        with pytest.raises(ValidationError):
            validate_area("mars")

    # ── validate_indicators ──
    def test_indicators_valid(self):
        result = validate_indicators(["RSI", "MACD"])
        assert isinstance(result, tuple)
        assert len(result) == 4  # (ids, versions, errors, warnings)

    def test_indicators_with_invalid(self):
        ids, vers, errors, warnings = validate_indicators(["RSI", "FAKE"])
        assert len(ids) >= 1  # RSI should be valid
        assert len(errors) >= 1  # FAKE should produce error

    # ── validate_symbol ──
    def test_symbol_valid(self):
        result = validate_symbol("NIFTY")
        assert result == "NIFTY"

    def test_symbol_empty(self):
        with pytest.raises(ValidationError):
            validate_symbol("")
