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
                "Stock exchange name (e.g., 'NSE', 'NASDAQ', 'BINANCE'). "
                f"Must be one of the valid exchanges like {', '.join(VALID_EXCHANGES[:5])}... "
                "Use uppercase format."
            ),
            min_length=2,
            max_length=30,
        ),
    ],
    symbol: Annotated[
        str,
        Field(
            description=(
                "Trading symbol/ticker (e.g., 'NIFTY', 'AAPL', 'BTCUSD'). "
                "Search online for correct symbol format for your exchange."
            ),
            min_length=1,
            max_length=20,
        ),
    ],
    timeframe: Annotated[
        str,
        Field(
            description=(
                "Time interval for each candle. Options: "
                "1m (1 minute), 5m, 15m, 30m, 1h (1 hour), 2h, 4h, "
                "1d (1 day), 1w (1 week), 1M (1 month)"
            ),
        ),
    ],
    numb_price_candles: Annotated[
        Union[int, str],
        Field(
            description=(
                "Number of historical candles to fetch (1-5000). "
                "Accepts int or str. More candles = longer history."
            ),
        ),
    ],
    indicators: Annotated[
        List[str],
        Field(
            description=(
                f"List of technical indicators to include. Options: "
                f"{', '.join(INDICATOR_MAPPING.keys())}. "
                "Example: ['RSI', 'MACD', 'CCI', 'BB']. Leave empty for no indicators."
            ),
        ),
    ] = [],  # noqa: B006
) -> str:
    """
    Fetch historical OHLCV data with technical indicators from TradingView.

    Retrieves historical price data (Open, High, Low, Close, Volume) for any
    trading instrument along with specified technical indicators.
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
