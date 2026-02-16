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
        str,
        Field(
            description=(
                "Trading symbol/ticker (e.g., 'NIFTY', 'AAPL', 'BTCUSD')."
            ),
            min_length=1,
            max_length=20,
        ),
    ],
    exchange: Annotated[
        str,
        Field(
            description=(
                f"Stock exchange name (e.g., 'NSE', 'NASDAQ', 'BITSTAMP'). "
                f"Must be one of: {', '.join(VALID_EXCHANGES[:5])}..."
            ),
            min_length=2,
            max_length=30,
        ),
    ] = "BITSTAMP",
    startPage: Annotated[
        Union[int, str],
        Field(
            description="Starting page number for scraping ideas (1-10).",
        ),
    ] = 1,
    endPage: Annotated[
        Union[int, str],
        Field(
            description="Ending page number for scraping ideas (1-10).",
        ),
    ] = 1,
    sort: Annotated[
        Literal["popular", "recent"],
        Field(
            description="Sorting order for ideas. 'popular' or 'recent'.",
        ),
    ] = "popular",
    start_datetime: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter ideas from this datetime onwards. "
                "IST format: 'DD-MM-YYYY HH:MM'."
            ),
        ),
    ] = None,
    end_datetime: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter ideas until this datetime. "
                "IST format: 'DD-MM-YYYY HH:MM'."
            ),
        ),
    ] = None,
) -> str:
    """
    Scrape trading ideas from TradingView for a specific symbol.

    Fetches trading ideas with title, author, publication time, and content.
    """
    try:
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
        str,
        Field(
            description=(
                "Trading symbol/ticker (e.g., 'NIFTY', 'AAPL', 'BTCUSD'). Required."
            ),
            min_length=1,
            max_length=20,
        ),
    ],
    exchange: Annotated[
        str,
        Field(
            description=(
                f"Stock exchange name (e.g., 'NSE', 'NASDAQ'). "
                f"Must be one of: {', '.join(VALID_EXCHANGES[:5])}..."
            ),
            min_length=2,
            max_length=30,
        ),
    ],
    limit: Annotated[
        Optional[Union[int, str]],
        Field(
            description=(
                "Maximum number of discussions to retrieve. "
                "If None, fetches all available."
            ),
        ),
    ] = None,
    start_datetime: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter discussions from this datetime onwards. "
                "IST format: 'DD-MM-YYYY HH:MM'."
            ),
        ),
    ] = None,
    end_datetime: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter discussions until this datetime. "
                "IST format: 'DD-MM-YYYY HH:MM'."
            ),
        ),
    ] = None,
) -> str:
    """
    Get community discussions (Minds) from TradingView for a specific symbol.

    Fetches community-generated discussions, questions, and sentiment.
    """
    try:
        parsed_limit: Optional[int] = None
        if limit is not None:
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
