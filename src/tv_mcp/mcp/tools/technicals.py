"""
MCP tool handler for technical indicators snapshot.
"""

from typing import Annotated

from pydantic import Field

from src.tv_mcp.core.validators import (
    VALID_EXCHANGES,
    VALID_TIMEFRAMES,
    ValidationError,
)
from src.tv_mcp.services.technicals import fetch_all_indicators

from ..serializers import serialize_error, serialize_success


async def get_all_indicators(
    symbol: Annotated[
        str,
        Field(
            description=(
                "Trading symbol/ticker (e.g., 'AAPL', 'BTCUSD', 'NIFTY'). REQUIRED."
            ),
            min_length=1,
            max_length=20,
        ),
    ],
    exchange: Annotated[
        str,
        Field(
            description=(
                "Stock exchange name (e.g., 'NASDAQ', 'BINANCE', 'NSE'). REQUIRED. "
                f"Valid examples: {', '.join(VALID_EXCHANGES[:5])}..."
            ),
            min_length=2,
            max_length=30,
        ),
    ],
    timeframe: Annotated[
        str,
        Field(
            description=(
                "Time interval for the technical indicator snapshot. REQUIRED. Valid options: "
                f"{', '.join(VALID_TIMEFRAMES)}"
            ),
        ),
    ] = "1m",
) -> str:
    """
    Retrieve real-time values for ALL available technical indicators for a given symbol.
    Provides a comprehensive snapshot of current technical signals (Buy/Sell levels, Oscillator values, MAs).
    """
    try:
        result = fetch_all_indicators(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
        )
        return serialize_success(result)
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")
