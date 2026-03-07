"""
Pydantic request models for the vercel HTTP API.

Field definitions mirror the legacy ``vercel/models.py`` but import
validation constants from the new ``src.tv_mcp.core.validators`` module.
"""

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from src.tv_mcp.core.validators import (
    VALID_TIMEFRAMES,
    VALID_NEWS_PROVIDERS,
    INDICATOR_MAPPING,
)


class HistoricalDataRequest(BaseModel):
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Stock exchange name. REQUIRED.",
    )
    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Trading symbol/ticker. REQUIRED.",
    )
    timeframe: str = Field(
        ...,
        description="Time interval for each candle. REQUIRED.",
    )
    numb_price_candles: int = Field(
        ...,
        description="Number of historical candles to fetch (1-5000). REQUIRED.",
    )
    indicators: List[str] = Field(
        default=[],
        description="List of technical indicators.",
    )


class NewsHeadlinesRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol/ticker for news. REQUIRED.")
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Stock exchange name. REQUIRED.",
    )
    provider: str = Field(
        "all",
        min_length=3,
        max_length=20,
        description="News provider filter.",
    )
    area: Literal["world", "americas", "europe", "asia", "oceania", "africa"] = Field(
        "world", description="Geographical area filter for news."
    )
    start_datetime: Optional[str] = Field(
        None, description="Filter news from this datetime onwards. IST format: DD-MM-YYYY HH:MM"
    )
    end_datetime: Optional[str] = Field(
        None, description="Filter news until this datetime. IST format: DD-MM-YYYY HH:MM"
    )


class NewsContentRequest(BaseModel):
    story_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of story IDs from news headlines. REQUIRED.",
    )


class AllIndicatorsRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol/ticker. REQUIRED.")
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Stock exchange name. REQUIRED.",
    )
    timeframe: str = Field(
        "1m",
        description="Time interval for indicator snapshot.",
    )


class IdeasRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol/ticker. REQUIRED.")
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Stock exchange name. REQUIRED.",
    )
    startPage: int = Field(1, description="Starting page number (1-10).")
    endPage: int = Field(1, description="Ending page number (1-10).")
    sort: Literal["popular", "recent"] = Field("popular", description="Sorting order for ideas.")
    start_datetime: Optional[str] = Field(
        None, description="Filter ideas from this datetime onwards. IST format: DD-MM-YYYY HH:MM"
    )
    end_datetime: Optional[str] = Field(
        None, description="Filter ideas until this datetime. IST format: DD-MM-YYYY HH:MM"
    )


class MindsRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol/ticker. REQUIRED.")
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Stock exchange name. REQUIRED.",
    )
    limit: int = Field(
        1, description="Maximum number of discussions to retrieve. Default is 1 for safety."
    )
    start_datetime: Optional[str] = Field(
        None, description="Filter discussions from this datetime onwards. IST format: DD-MM-YYYY HH:MM"
    )
    end_datetime: Optional[str] = Field(
        None, description="Filter discussions until this datetime. IST format: DD-MM-YYYY HH:MM"
    )


class OptionChainGreeksRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Underlying symbol. REQUIRED.")
    exchange: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Stock exchange name. REQUIRED.",
    )
    expiry_date: Optional[Union[int, str]] = Field(
        "nearest",
        description=(
            "Option expiry date: 'nearest' (default), 'all', or int YYYYMMDD (e.g., 20251202)."
        ),
    )
    no_of_ITM: int = Field(5, description="Number of In-The-Money strikes (1-20).")
    no_of_OTM: int = Field(5, description="Number of Out-of-The-Money strikes (1-20).")


class NseOptionChainOiRequest(BaseModel):
    symbol: str = Field(..., description="NSE Index symbol (e.g. NIFTY). REQUIRED.")
    expiry_date: str = Field(..., description="NSE expiry format 'DD-MMM-YYYY'. REQUIRED.")


# ── PAPER TRADING REQUEST MODELS ─────────────────────────────────


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=30, description="Trading symbol. REQUIRED.")
    exchange: str = Field(..., min_length=2, max_length=30, description="Exchange. REQUIRED.")
    stop_loss: float = Field(..., gt=0, description="Stop loss price. REQUIRED.")
    target: float = Field(..., gt=0, description="Target/take-profit price. REQUIRED.")
    lot_size: int = Field(..., gt=0, description="Number of lots/quantity. REQUIRED.")
    entry_price: Optional[float] = Field(
        None, gt=0,
        description="Entry/limit price. Required for LIMIT orders, ignored for MARKET.",
    )
    order_type: str = Field(
        "LIMIT",
        description="Order type: 'MARKET' or 'LIMIT' (default).",
    )
    trailing_sl_step_pct: Optional[float] = Field(
        None,
        description=(
            "Trailing SL step as % of current price (e.g. 0.5). "
            "Providing this value enables trailing SL. Omit to disable."
        ),
    )


class ClosePositionRequest(BaseModel):
    order_id: int = Field(..., description="Order ID of the position to close. REQUIRED.")


class ViewPositionsRequest(BaseModel):
    filter_type: Optional[str] = Field(
        None, description="Filter: 'pending', 'open', 'closed', or 'all'."
    )
    order_id: Optional[int] = Field(None, description="Specific order ID to view.")


class SetAlertRequest(BaseModel):
    alert_type: str = Field(..., description="Alert type: 'price' or 'time'. REQUIRED.")
    symbol: Optional[str] = Field(None, description="Symbol for price alert.")
    exchange: Optional[str] = Field(None, description="Exchange for price alert.")
    price: Optional[float] = Field(
        None,
        description=(
            "Target price level. Direction is auto-detected from current market price."
        ),
    )
    minutes: Optional[int] = Field(None, gt=0, description="Minutes for time alert.")


class RemoveAlertRequest(BaseModel):
    alert_id: int = Field(..., description="Alert ID to remove. REQUIRED.")


# ── RESPONSE MODELS (Needed for valid OpenAPI schemas) ────────────


class HealthResponse(BaseModel):
    status: str = Field(..., description="Status of the service.")
    service: str = Field(..., description="Name of the service.")


class GenericDataResponse(BaseModel):
    data: Union[str, dict, list] = Field(
        ...,
        description="The response data, usually a TOON-encoded string or a structured object.",
    )
