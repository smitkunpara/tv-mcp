"""
MCP tool handler for technical indicators snapshot.
"""

from typing import Annotated, Optional

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
        Optional[str],
        Field(
            description=(
                "Trading symbol/ticker (e.g., 'AAPL', 'BTCUSD', 'NIFTY'). REQUIRED."
            ),
        ),
    ] = None,
    exchange: Annotated[
        Optional[str],
        Field(
            description=(
                "Stock exchange name (e.g., 'NASDAQ', 'BINANCE', 'NSE'). REQUIRED."
            ),
        ),
    ] = None,
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
    """
    try:
        if not exchange:
            return serialize_error("Missing REQUIRED field: 'exchange'. Please specify the exchange (e.g., 'NASDAQ').")
        if not symbol:
            return serialize_error("Missing REQUIRED field: 'symbol'. Please specify the ticker (e.g., 'AAPL').")

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
