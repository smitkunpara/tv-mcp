"""
MCP tool handler for historical OHLCV data.
"""

from typing import Annotated, List, Union, Optional

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
        Optional[str],
        Field(
            description=(
                "Stock exchange name where the symbol is traded (e.g., 'NASDAQ', 'BINANCE', 'NSE'). REQUIRED."
            ),
        ),
    ] = None,
    symbol: Annotated[
        Optional[str],
        Field(
            description=(
                "Trading symbol/ticker (e.g., 'AAPL', 'BTCUSD', 'NIFTY'). REQUIRED."
            ),
        ),
    ] = None,
    timeframe: Annotated[
        Optional[str],
        Field(
            description=(
                "Time interval for each price candle. REQUIRED. Options: "
                "1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M"
            ),
        ),
    ] = None,
    numb_price_candles: Annotated[
        Optional[Union[int, str]],
        Field(
            description=(
                "Number of historical candles to fetch (1-5000). REQUIRED."
            ),
        ),
    ] = None,
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
    Use this to identify historical trends and patterns.
    """
    try:
        if not exchange:
            return serialize_error("Missing REQUIRED field: 'exchange'. Please specify the exchange (e.g., 'NASDAQ').")
        if not symbol:
            return serialize_error("Missing REQUIRED field: 'symbol'. Please specify the ticker (e.g., 'AAPL').")
        if not timeframe:
            return serialize_error("Missing REQUIRED field: 'timeframe'. Please specify the interval (e.g., '1h').")
        if numb_price_candles is None:
            return serialize_error("Missing REQUIRED field: 'numb_price_candles'. Please specify how many candles to fetch (1-5000).")

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
