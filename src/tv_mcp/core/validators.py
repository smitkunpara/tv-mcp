"""
Validators for tv_mcp using tv_scraper validation constants.
"""

import importlib
from typing import Any, List, Optional, Tuple

from tv_scraper.core.exceptions import ValidationError

__all__ = [
    "ValidationError",
    "VALID_EXCHANGES",
    "VALID_TIMEFRAMES",
    "VALID_NEWS_PROVIDERS",
    "VALID_AREAS",
    "get_valid_indicator_mapping",
    "get_valid_indicators",
]

# Re-expose common lists for MCP tool descriptions
def _load_validation_constants() -> tuple[list[str], list[str], list[str], list[str]]:
    """Load validation constants from tv_scraper across old/new versions."""
    try:
        validation_data = importlib.import_module("tv_scraper.core.validation_data")
        exchanges = sorted(getattr(validation_data, "EXCHANGES"))
        timeframes = list(getattr(validation_data, "TIMEFRAMES").keys())
        providers = sorted(getattr(validation_data, "NEWS_PROVIDERS"))
        areas = list(getattr(validation_data, "AREAS").keys())
        return exchanges, timeframes, providers, areas
    except Exception:
        validators_mod = importlib.import_module("tv_scraper.core.validators")
        validator_cls = getattr(validators_mod, "DataValidator")
        validator = validator_cls()
        exchanges = sorted(validator.get_exchanges())
        timeframes = list(validator.get_timeframes().keys())
        providers = sorted(validator.get_news_providers())
        areas = list(validator.get_areas().keys())
        return exchanges, timeframes, providers, areas


VALID_EXCHANGES, VALID_TIMEFRAMES, VALID_NEWS_PROVIDERS, VALID_AREAS = _load_validation_constants()

_EXCHANGE_SET = set(VALID_EXCHANGES)
_TIMEFRAME_SET = set(VALID_TIMEFRAMES)
_NEWS_PROVIDER_SET = set(VALID_NEWS_PROVIDERS)
_AREA_SET = set(VALID_AREAS)

# Fallback indicator mapping when live fetch fails.
_DEFAULT_INDICATOR_MAPPING = {
    "RSI": ("STD;RSI", "44.0"),
    "MACD": ("STD;MACD", "38.0"),
    "CCI": ("STD;CCI", "37.0"),
    "BB": ("STD;Bollinger_Bands", "32.0"),
}

# Backward-compatible constant; live mapping is served via get_valid_indicator_mapping().
INDICATOR_MAPPING = dict(_DEFAULT_INDICATOR_MAPPING)

_INDICATOR_MAPPING_CACHE: Optional[dict[str, tuple[str, str]]] = None
_INDICATOR_NAMES_CACHE: Optional[dict[str, str]] = None


def _fetch_live_indicator_mapping() -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    """Fetch indicator name/id/version catalog from tv_scraper streaming utils."""
    utils_mod = importlib.import_module("tv_scraper.streaming.utils")
    fetch_fn = getattr(utils_mod, "fetch_available_indicators")
    response = fetch_fn()

    if not isinstance(response, dict) or response.get("status") != "success":
        return {}, {}

    items = response.get("data")
    if not isinstance(items, list):
        return {}, {}

    mapping: dict[str, tuple[str, str]] = {}
    names: dict[str, str] = {}
    id_to_version: dict[str, str] = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        raw_name = item.get("name")
        raw_id = item.get("id")
        raw_version = item.get("version")
        if not raw_name or not raw_id or not raw_version:
            continue

        display_name = str(raw_name).strip()
        normalized = display_name.upper()
        indicator_id = str(raw_id).strip()
        indicator_version = str(raw_version).strip()
        mapping[normalized] = (indicator_id, indicator_version)
        names[normalized] = display_name
        id_to_version[indicator_id] = indicator_version

    # Keep short aliases stable for existing clients while using latest live versions.
    for alias_name, (alias_id, fallback_version) in _DEFAULT_INDICATOR_MAPPING.items():
        mapping[alias_name] = (alias_id, id_to_version.get(alias_id, fallback_version))
        names[alias_name] = alias_name

    return mapping, names


def get_valid_indicator_mapping(force_refresh: bool = False) -> dict[str, tuple[str, str]]:
    """Return valid indicator -> (script_id, version) mapping for candle streaming."""
    global _INDICATOR_MAPPING_CACHE, _INDICATOR_NAMES_CACHE

    if _INDICATOR_MAPPING_CACHE is not None and not force_refresh:
        return _INDICATOR_MAPPING_CACHE

    mapping: dict[str, tuple[str, str]]
    names: dict[str, str]

    try:
        mapping, names = _fetch_live_indicator_mapping()
    except Exception:
        mapping, names = {}, {}

    if not mapping:
        mapping = dict(_DEFAULT_INDICATOR_MAPPING)
        names = {k: k for k in mapping.keys()}

    _INDICATOR_MAPPING_CACHE = mapping
    _INDICATOR_NAMES_CACHE = names
    return _INDICATOR_MAPPING_CACHE


def get_valid_indicators(force_refresh: bool = False) -> List[str]:
    """Return display names for all currently valid candle-stream indicators."""
    global _INDICATOR_NAMES_CACHE

    get_valid_indicator_mapping(force_refresh=force_refresh)
    if not _INDICATOR_NAMES_CACHE:
        return sorted(_DEFAULT_INDICATOR_MAPPING.keys())
    return sorted(_INDICATOR_NAMES_CACHE.values())

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
VALID_INDICATORS = list(_DEFAULT_INDICATOR_MAPPING.keys())

# ── OI supported symbols by exchange ───────────────────────────────
VALID_NSE_INDICES = ["NIFTY", "NIFTYNXT50", "FINNIFTY", "BANKNIFTY", "MIDCPNIFTY"]
VALID_BSE_INDICES = ["SENSEX", "BANKEX", "SX50"]

VALID_OI_EXCHANGES = {
    "NSE": VALID_NSE_INDICES,
    "BSE": VALID_BSE_INDICES,
}


def validate_exchange(exchange: str) -> str:
    normalized = (exchange or "").strip().upper()
    if normalized in _EXCHANGE_SET:
        return normalized

    exchanges = sorted(VALID_EXCHANGES)
    raise ValidationError(
        f"Invalid exchange: '{exchange}'. "
        f"Please provide a valid exchange from the following list: {', '.join(exchanges)}"
    )


def validate_symbol(symbol: str) -> str:
    # Use generic non-empty validation since we don't always have exchange here
    if not symbol or not symbol.strip():
        raise ValidationError("Symbol is required and cannot be empty.")
    return symbol.strip()


def validate_oi_symbol(exchange: str, symbol: str) -> str:
    normalized_exchange = exchange.upper().strip()
    normalized_symbol = validate_symbol(symbol).upper()

    if normalized_exchange not in VALID_OI_EXCHANGES:
        supported_exchanges = ", ".join(sorted(VALID_OI_EXCHANGES.keys()))
        raise ValidationError(
            f"Invalid exchange: '{exchange}'. OI data supports only: {supported_exchanges}."
        )

    supported_symbols = VALID_OI_EXCHANGES[normalized_exchange]
    if normalized_symbol not in supported_symbols:
        raise ValidationError(
            f"Symbol '{normalized_symbol}' is not supported on exchange '{normalized_exchange}' for OI data. "
            f"Supported symbols for {normalized_exchange}: {', '.join(supported_symbols)}"
        )

    return normalized_symbol


def validate_timeframe(timeframe: str) -> str:
    normalized = (timeframe or "").strip()
    if normalized in _TIMEFRAME_SET:
        return normalized

    timeframes = sorted(VALID_TIMEFRAMES)
    raise ValidationError(
        f"Invalid timeframe: '{timeframe}'. "
        f"Valid options are: {', '.join(timeframes)}"
    )


def validate_news_provider(provider: Optional[str]) -> Optional[str]:
    if not provider or provider.lower() == "all":
        return None

    if provider not in _NEWS_PROVIDER_SET:
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
    normalized = (area or "").strip().lower()
    if normalized not in _AREA_SET:
        raise ValidationError(f"Invalid area: {area}. Allowed: {', '.join(VALID_AREAS)}")
    return normalized


def validate_indicators(indicators: List[str]) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Validate and map indicator names to TradingView IDs for Streamer."""
    indicator_ids: List[str] = []
    indicator_versions: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    indicator_mapping = get_valid_indicator_mapping()
    valid_names = get_valid_indicators()

    for indicator in indicators:
        indicator_upper = indicator.upper()
        if indicator_upper in indicator_mapping:
            ind_id, ind_version = indicator_mapping[indicator_upper]
            indicator_ids.append(ind_id)
            indicator_versions.append(ind_version)
        else:
            valid_list = ", ".join(valid_names)
            errors.append(
                f"Indicator '{indicator}' not recognized. "
                f"Valid options are: {valid_list}"
            )

    return indicator_ids, indicator_versions, errors, warnings
