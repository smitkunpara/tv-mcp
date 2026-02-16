"""
MCP tool handler for historical OHLCV data.
"""

from typing import Annotated, List, Union

from pydantic import Field

from src.tv_mcp.core.validators import (
    INDICATOR_MAPPING,
    ValidationError,
)
from src.tv_mcp.services.historical import fetch_historical_data

from ..serializers import serialize_error, serialize_success


async def get_historical_data(
    exchange: Annotated[
        str,
        Field(
            description=(
                "Stock exchange name where the symbol is traded (e.g., 'NASDAQ', 'BINANCE', 'NSE'). REQUIRED."
            ),
        ),
    ],
    symbol: Annotated[
        str,
        Field(
            description=(
                "Trading symbol/ticker (e.g., 'AAPL', 'BTCUSD', 'NIFTY'). REQUIRED."
            ),
        ),
    ],
    timeframe: Annotated[
        str,
        Field(
            description=(
                "Time interval for each price candle. REQUIRED. Options: "
                "1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M"
            ),
        ),
    ],
    numb_price_candles: Annotated[
        Union[int, str],
        Field(
            description=(
                "Number of historical candles to fetch (1-5000). REQUIRED."
            ),
        ),
    ],
    indicators: Annotated[
        List[str],
        Field(
            description=(
                f"List of technical indicators to overlay. "
                f"Options: {', '.join(INDICATOR_MAPPING.keys())}."
            ),
        ),
    ] = [],  # noqa: B006
) -> str:
    """
    Fetch historical OHLCV data with technical indicators. 
    Supports stocks, indices, crypto, options (e.g. 'NSE:NIFTY260219C24000'), and futures.
    Use this to identify trends and patterns across any TradingView-supported asset.

    NOTE: When fetching historical data for Indices (like NIFTY), the volume represents the 
    underlying market activity, not the option lot volume seen in NSE OI tools.
    """
    try:
        # Pydantic or coercion handled by FastMCP, but we ensure it's int for the service
        count = int(numb_price_candles)
        
        result = fetch_historical_data(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            numb_price_candles=count,
            indicators=indicators,
        )
        return serialize_success(result)
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")
