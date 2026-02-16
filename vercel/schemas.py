"""
Pydantic request models for the vercel HTTP API.

Field definitions mirror the legacy ``vercel/models.py`` but import
validation constants from the new ``src.tv_mcp.core.validators`` module.
"""

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from src.tv_mcp.core.validators import (
    VALID_EXCHANGES,
    VALID_TIMEFRAMES,
    VALID_NEWS_PROVIDERS,
    INDICATOR_MAPPING,
)


class HistoricalDataRequest(BaseModel):
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description=(
            f"Stock exchange name (e.g., 'NSE', 'NASDAQ', 'BINANCE'). "
            f"Must be one of the valid exchanges like {', '.join(VALID_EXCHANGES[:5])}... "
            "Use uppercase format."
        ),
    )
    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Trading symbol/ticker (e.g., 'NIFTY', 'AAPL', 'BTCUSD').",
    )
    timeframe: str = Field(
        ...,
        description=(
            "Time interval for each candle. Options: "
            "1m (1 minute), 5m, 15m, 30m, 1h (1 hour), 2h, 4h, 1d (1 day), 1w (1 week), 1M (1 month)"
        ),
    )
    numb_price_candles: Union[int, str] = Field(
        ...,
        description="Number of historical candles to fetch (1-5000). Accepts int or str.",
    )
    indicators: List[str] = Field(
        default=[],
        description=f"List of technical indicators. Options: {', '.join(INDICATOR_MAPPING.keys())}.",
    )


class NewsHeadlinesRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol/ticker for news. REQUIRED.")
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description=f"Stock exchange name. REQUIRED. One of: {', '.join(VALID_EXCHANGES[:5])}...",
    )
    provider: str = Field(
        "all",
        min_length=3,
        max_length=20,
        description=f"News provider filter. Options: {', '.join(VALID_NEWS_PROVIDERS)}.",
    )
    area: Literal["world", "americas", "europe", "asia", "oceania", "africa"] = Field(
        "asia", description="Geographical area filter for news."
    )
    start_datetime: Optional[str] = Field(
        None, description="Filter news from this datetime onwards. IST format: DD-MM-YYYY HH:MM"
    )
    end_datetime: Optional[str] = Field(
        None, description="Filter news until this datetime. IST format: DD-MM-YYYY HH:MM"
    )


class NewsContentRequest(BaseModel):
    story_paths: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of story paths from news headlines. Each path must start with '/news/'.",
    )


class AllIndicatorsRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol/ticker.")
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description=f"Stock exchange name. Valid examples: {', '.join(VALID_EXCHANGES[:5])}...",
    )
    timeframe: str = Field(
        "1m",
        description=f"Time interval for indicator snapshot. Valid options: {', '.join(VALID_TIMEFRAMES)}",
    )


class IdeasRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol/ticker.")
    exchange: str = Field(
        "BITSTAMP",
        min_length=2,
        max_length=30,
        description=f"Stock exchange name. Valid examples: {', '.join(VALID_EXCHANGES[:5])}...",
    )
    startPage: Union[int, str] = Field(1, description="Starting page number (1-10).")
    endPage: Union[int, str] = Field(1, description="Ending page number (1-10).")
    sort: Literal["popular", "recent"] = Field("popular", description="Sorting order for ideas.")
    start_datetime: Optional[str] = Field(
        None, description="Filter ideas from this datetime onwards. IST format: DD-MM-YYYY HH:MM"
    )
    end_datetime: Optional[str] = Field(
        None, description="Filter ideas until this datetime. IST format: DD-MM-YYYY HH:MM"
    )


class MindsRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol/ticker.")
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description=f"Stock exchange name. Valid examples: {', '.join(VALID_EXCHANGES[:5])}...",
    )
    limit: Optional[Union[int, str]] = Field(
        None, description="Maximum number of discussions to retrieve."
    )
    start_datetime: Optional[str] = Field(
        None, description="Filter discussions from this datetime onwards. IST format: DD-MM-YYYY HH:MM"
    )
    end_datetime: Optional[str] = Field(
        None, description="Filter discussions until this datetime. IST format: DD-MM-YYYY HH:MM"
    )


class OptionChainGreeksRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Underlying symbol.")
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description=f"Stock exchange name. Valid examples: {', '.join(VALID_EXCHANGES[:5])}...",
    )
    expiry_date: Optional[Union[int, str]] = Field(
        "nearest",
        description=(
            "Option expiry date: 'nearest' (default), 'all', or int YYYYMMDD (e.g., 20251202)."
        ),
    )
    no_of_ITM: Union[int, str] = Field(5, description="Number of In-The-Money strikes (1-20).")
    no_of_OTM: Union[int, str] = Field(5, description="Number of Out-of-The-Money strikes (1-20).")
