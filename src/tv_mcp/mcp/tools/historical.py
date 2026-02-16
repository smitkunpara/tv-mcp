"""
MCP tool handler for historical OHLCV data.
"""

from typing import Annotated, List, Union

from pydantic import Field

from src.tv_mcp.core.validators import (
    INDICATOR_MAPPING,
    VALID_EXCHANGES,
    VALID_TIMEFRAMES,
    ValidationError,
)
from src.tv_mcp.services.historical import fetch_historical_data

from ..serializers import serialize_error, serialize_success


async def get_historical_data(
    exchange: Annotated[
        str,
        Field(
            description=(
                "Stock exchange name where the symbol is traded (e.g., 'NASDAQ', 'BINANCE', 'NSE'). REQUIRED. "
                f"Must be one of the valid exchanges like {', '.join(VALID_EXCHANGES[:5])}..."
            ),
            min_length=2,
            max_length=30,
        ),
    ],
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
                "Number of historical candles to fetch (1-5000). REQUIRED. "
                "More candles provide longer historical context."
            ),
        ),
    ],
    indicators: Annotated[
        List[str],
        Field(
            description=(
                f"List of technical indicators to overlay on price data. "
                f"Options: {', '.join(INDICATOR_MAPPING.keys())}. "
                "Example: ['RSI', 'MACD']. Leave empty for OHLCV only."
            ),
        ),
    ] = [],  # noqa: B006
) -> str:
    """
    Fetch historical OHLCV (Open, High, Low, Close, Volume) data with optional technical indicators.
    Use this tool to perform technical analysis and identify historical price trends for any symbol.
    """
    try:
        numb_price_candles = (
            int(numb_price_candles)
            if isinstance(numb_price_candles, str)
            else numb_price_candles
        )
        if not (1 <= numb_price_candles <= 5000):
            raise ValidationError(
                f"numb_price_candles must be between 1 and 5000, got {numb_price_candles}"
            )
        result = fetch_historical_data(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            numb_price_candles=numb_price_candles,
            indicators=indicators,
        )
        return serialize_success(result)
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")
