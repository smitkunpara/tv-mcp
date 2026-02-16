"""
Validators for tv_mcp using tv_scraper's DataValidator.
"""

from typing import Any, Dict, List, Optional, Tuple
from tv_scraper.core.validators import DataValidator
from tv_scraper.core.exceptions import ValidationError

__all__ = ["validator", "ValidationError", "VALID_EXCHANGES", "VALID_TIMEFRAMES", "VALID_NEWS_PROVIDERS", "VALID_AREAS"]

# Singleton instance for the MCP project
validator = DataValidator()

# Re-expose common lists for MCP tool descriptions
VALID_EXCHANGES = validator.get_exchanges()
VALID_TIMEFRAMES = list(validator.get_timeframes().keys())
VALID_NEWS_PROVIDERS = validator.get_news_providers()
VALID_AREAS = list(validator.get_areas().keys())

# Indicator mapping for Streamer (WebSocket)
# These are kept here as they map common names to TV's internal IDs
INDICATOR_MAPPING = {
    "RSI": ("STD;RSI", "44.0"),
    "MACD": ("STD;MACD", "38.0"),
    "CCI": ("STD;CCI", "37.0"),
    "BB": ("STD;Bollinger_Bands", "32.0"),
}

# Mapping internal TV field indices to human-readable names
INDICATOR_FIELD_MAPPING = {
    "RSI": {
        "2": "Relative_Strength_Index",
        "0": "Relative_Strength_Index_Moving_Average",
    },
    "MACD": {
        "4": "Moving_Average_Convergence_Divergence_macd",
        "5": "Moving_Average_Convergence_Divergence_signal",
        "2": "Moving_Average_Convergence_Divergence_histogram",
    },
    "CCI": {
        "0": "Commodity_Channel_Index",
        "1": "Commodity_Channel_Index_Moving_Average",
    },
    "BB": {
        "0": "Bollinger_Bands_middle_line",
        "1": "Bollinger_Bands_top_line",
        "2": "Bollinger_Bands_bottom_line",
    },
}
VALID_INDICATORS = list(INDICATOR_MAPPING.keys())

# ── NSE supported symbols ──────────────────────────────────────────
VALID_NSE_INDICES = ["NIFTY", "NIFTYNXT50", "FINNIFTY", "BANKNIFTY", "MIDCPNIFTY"]


def validate_exchange(exchange: str) -> str:
    validator.validate_exchange(exchange)
    return exchange.upper()


def validate_symbol(symbol: str) -> str:
    # Use generic non-empty validation since we don't always have exchange here
    if not symbol or not symbol.strip():
        raise ValidationError("Symbol is required and cannot be empty.")
    return symbol.strip()


def validate_timeframe(timeframe: str) -> str:
    validator.validate_timeframe(timeframe)
    return timeframe


def validate_news_provider(provider: Optional[str]) -> Optional[str]:
    if not provider or provider.lower() == "all":
        return None
    providers = validator.get_news_providers()
    if provider not in providers:
        raise ValidationError(f"Invalid news provider: '{provider}'. Please provide a valid provider name (e.g., 'tradingview', 'dow-jones') or use 'all'.")
    return provider


def validate_candle_count(count: Any) -> int:
    """Validate and coerce candle count with AI-friendly error."""
    if count is None:
        raise ValidationError("The 'numb_price_candles' field is REQUIRED. Please specify how many historical candles you need (1-5000).")
    try:
        val = int(count)
        if not (1 <= val <= 5000):
            raise ValidationError(f"The 'numb_price_candles' must be between 1 and 5000. Received: {val}")
        return val
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid candle count: '{count}'. Must be a valid integer between 1 and 5000.")


def validate_area(area: str) -> str:
    areas = validator.get_areas()
    if area not in areas:
        raise ValidationError(f"Invalid area: {area}. Allowed: {', '.join(areas.keys())}")
    return area


def validate_indicators(indicators: List[str]) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Validate and map indicator names to TradingView IDs for Streamer."""
    indicator_ids: List[str] = []
    indicator_versions: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    for indicator in indicators:
        indicator_upper = indicator.upper()
        if indicator_upper in INDICATOR_MAPPING:
            ind_id, ind_version = INDICATOR_MAPPING[indicator_upper]
            indicator_ids.append(ind_id)
            indicator_versions.append(ind_version)
        else:
            errors.append(f"Indicator '{indicator}' not recognized.")

    return indicator_ids, indicator_versions, errors, warnings
