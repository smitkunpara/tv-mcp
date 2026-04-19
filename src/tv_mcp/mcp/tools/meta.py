"""
MCP tool handlers for metadata (exchanges, timeframes, indicators).
"""

from src.tv_mcp.core.validators import (
    VALID_EXCHANGES,
    VALID_TIMEFRAMES,
    get_valid_indicators,
)
from ..serializers import serialize_success


async def list_available_exchanges() -> str:
    """
    Retrieve a list of all supported stock/crypto exchanges on TradingView.
    Use this if you are unsure about the correct exchange name for a symbol.
    """
    return serialize_success({"exchanges": sorted(VALID_EXCHANGES)})


async def list_supported_indicators() -> str:
    """
    Retrieve a list of all technical indicators supported by the historical data tool.
    These can be used in the 'indicators' list parameter of get_historical_data.
    """
    return serialize_success({
        "indicators": get_valid_indicators(),
        "guidance": (
            "These indicators are mapped to TradingView's internal IDs and can be "
            "overlaid on historical OHLCV data."
        )
    })


async def list_available_timeframes() -> str:
    """
    Retrieve a list of all valid timeframe strings supported by the server.
    """
    return serialize_success({"timeframes": sorted(VALID_TIMEFRAMES)})
