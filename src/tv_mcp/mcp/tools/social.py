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
                "Trading symbol/ticker (e.g., 'BTCUSD', 'TSLA'). REQUIRED."
            ),
            min_length=1,
            max_length=20,
        ),
    ],
    exchange: Annotated[
        str,
        Field(
            description=(
                "Stock exchange name (e.g., 'NASDAQ', 'BITSTAMP'). REQUIRED. "
                f"Must be one of: {', '.join(VALID_EXCHANGES[:5])}..."
            ),
            min_length=2,
            max_length=30,
        ),
    ],
    startPage: Annotated[
        Union[int, str],
        Field(
            description="Starting page number for scraping (usually 1).",
        ),
    ] = 1,
    endPage: Annotated[
        Union[int, str],
        Field(
            description="Ending page number for scraping (max 10).",
        ),
    ] = 1,
    sort: Annotated[
        Literal["popular", "recent"],
        Field(
            description="Sort criteria for ideas. Use 'popular' for validated community sentiment.",
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
    Analyze these to understand Retail and Pro trader sentiment for a symbol.
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
                "Trading symbol/ticker (e.g., 'NIFTY', 'AAPL'). REQUIRED."
            ),
            min_length=1,
            max_length=20,
        ),
    ],
    exchange: Annotated[
        str,
        Field(
            description=(
                "Stock exchange name (e.g., 'NSE', 'NASDAQ'). REQUIRED. "
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
                "Max number of discussions to retrieve (e.g., 50)."
            ),
        ),
    ] = None,
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
    Get community discussions, questions, and quick sentiment from TradingView Minds.
    Useful for identifying real-time crowd-sourced insights and trending topics.
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
