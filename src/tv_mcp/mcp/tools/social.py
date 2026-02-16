"""
MCP tool handlers for community content (Ideas & Minds).
"""

from typing import Annotated, Literal, Optional, Union

from pydantic import Field

from src.tv_mcp.core.validators import VALID_EXCHANGES, ValidationError
from src.tv_mcp.services.ideas import fetch_ideas
from src.tv_mcp.services.minds import fetch_minds

from ..serializers import serialize_error, serialize_success


async def get_ideas(
    symbol: Annotated[
        Optional[str],
        Field(
            description=(
                "Trading symbol/ticker (e.g., 'BTCUSD', 'TSLA'). REQUIRED."
            ),
        ),
    ] = None,
    exchange: Annotated[
        Optional[str],
        Field(
            description=(
                "Stock exchange name (e.g., 'NASDAQ', 'BITSTAMP'). REQUIRED."
            ),
        ),
    ] = None,
    startPage: Annotated[
        Union[int, str],
        Field(
            description="Starting page number for scraping. Default is 1 for safety.",
        ),
    ] = 1,
    endPage: Annotated[
        Union[int, str],
        Field(
            description="Ending page number for scraping. Default is 1 for safety.",
        ),
    ] = 1,
    sort: Annotated[
        Literal["popular", "recent"],
        Field(
            description="Sort criteria for ideas. Default is 'popular'.",
        ),
    ] = "popular",
    start_datetime: Annotated[
        Optional[str],
        Field(
            description="Filter ideas published AFTER this date-time. Format: 'DD-MM-YYYY HH:MM' in IST.",
        ),
    ] = None,
    end_datetime: Annotated[
        Optional[str],
        Field(
            description="Filter ideas published BEFORE this date-time. Format: 'DD-MM-YYYY HH:MM' in IST.",
        ),
    ] = None,
) -> str:
    """
    Scrape user-published trading ideas from TradingView community.
    """
    try:
        if not exchange:
            return serialize_error("Missing REQUIRED field: 'exchange'. Please specify the exchange (e.g., 'BITSTAMP').")
        if not symbol:
            return serialize_error("Missing REQUIRED field: 'symbol'. Please specify the ticker (e.g., 'BTCUSD').")

        result = fetch_ideas(
            symbol=symbol,
            exchange=exchange,
            startPage=int(startPage) if isinstance(startPage, str) else startPage,
            endPage=int(endPage) if isinstance(endPage, str) else endPage,
            sort=sort,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        return serialize_success(result)
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def get_minds(
    symbol: Annotated[
        Optional[str],
        Field(
            description=(
                "Trading symbol/ticker (e.g., 'NIFTY', 'AAPL'). REQUIRED."
            ),
        ),
    ] = None,
    exchange: Annotated[
        Optional[str],
        Field(
            description=(
                "Stock exchange name (e.g., 'NSE', 'NASDAQ'). REQUIRED."
            ),
        ),
    ] = None,
    limit: Annotated[
        Union[int, str],
        Field(
            description=(
                "Max number of discussions to retrieve. Default is 1 for safety."
            ),
        ),
    ] = 1,
    start_datetime: Annotated[
        Optional[str],
        Field(
            description="Filter discussions created AFTER this date-time. Format: 'DD-MM-YYYY HH:MM' in IST.",
        ),
    ] = None,
    end_datetime: Annotated[
        Optional[str],
        Field(
            description="Filter discussions created BEFORE this date-time. Format: 'DD-MM-YYYY HH:MM' in IST.",
        ),
    ] = None,
) -> str:
    """
    Get community discussions, questions, and sentiment from TradingView Minds.
    """
    try:
        if not exchange:
            return serialize_error("Missing REQUIRED field: 'exchange'. Please specify the exchange (e.g., 'NSE').")
        if not symbol:
            return serialize_error("Missing REQUIRED field: 'symbol'. Please specify the ticker (e.g., 'NIFTY').")

        parsed_limit = int(limit) if isinstance(limit, str) else limit
        result = fetch_minds(
            symbol=symbol,
            exchange=exchange,
            limit=parsed_limit,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        return serialize_success(result)
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")
