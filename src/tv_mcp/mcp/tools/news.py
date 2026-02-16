"""
MCP tool handlers for news headlines and article content.
"""

from typing import Annotated, List, Literal, Optional

from pydantic import Field

from src.tv_mcp.core.validators import (
    VALID_EXCHANGES,
    VALID_NEWS_PROVIDERS,
    ValidationError,
)
from src.tv_mcp.services.news import fetch_news_content, fetch_news_headlines

from ..serializers import serialize_error, serialize_success


async def get_news_headlines(
    symbol: Annotated[
        str,
        Field(
            description=(
                "Trading symbol for news (e.g., 'NIFTY', 'AAPL', 'BTC'). Required."
            ),
            min_length=1,
            max_length=20,
        ),
    ],
    exchange: Annotated[
        Optional[str],
        Field(
            description=(
                f"Optional exchange filter. One of: {', '.join(VALID_EXCHANGES[:5])}..."
            ),
            min_length=2,
            max_length=30,
        ),
    ] = None,
    provider: Annotated[
        str,
        Field(
            description=(
                f"News provider filter. Options: {', '.join(VALID_NEWS_PROVIDERS[:5])}... "
                "or 'all' for all providers."
            ),
            min_length=3,
            max_length=20,
        ),
    ] = "all",
    area: Annotated[
        Literal["world", "americas", "europe", "asia", "oceania", "africa"],
        Field(description="Geographical area filter for news. Default is 'asia'."),
    ] = "asia",
    start_datetime: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter news from this datetime onwards. "
                "IST format: 'DD-MM-YYYY HH:MM'."
            ),
        ),
    ] = None,
    end_datetime: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter news until this datetime. "
                "IST format: 'DD-MM-YYYY HH:MM'."
            ),
        ),
    ] = None,
) -> str:
    """
    Scrape latest news headlines from TradingView for a specific symbol.

    Returns structured headline data including title, source,
    publication time, and story paths for fetching full content.
    """
    try:
        headlines = fetch_news_headlines(
            symbol=symbol,
            exchange=exchange,
            provider=provider,
            area=area,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        if not headlines:
            return serialize_success({"headlines": []})
        return serialize_success({"headlines": headlines})
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def get_news_content(
    story_paths: Annotated[
        List[str],
        Field(
            description=(
                "List of story paths from news headlines. "
                "Each path must start with '/news/'. "
                "Get these from get_news_headlines() results."
            ),
            min_length=1,
            max_length=20,
        ),
    ],
) -> str:
    """
    Fetch full news article content using story paths from headlines.

    Retrieves the complete article text for news stories using the story paths
    obtained from get_news_headlines().
    """
    try:
        articles = fetch_news_content(story_paths)
        return serialize_success({"articles": articles})
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")
