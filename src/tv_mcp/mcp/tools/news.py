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
                "Trading symbol/ticker for news (e.g., 'AAPL', 'BTCUSD'). REQUIRED."
            ),
            min_length=1,
            max_length=20,
        ),
    ],
    exchange: Annotated[
        str,
        Field(
            description=(
                "Stock exchange name where the symbol is traded (e.g., 'NASDAQ', 'BINANCE'). REQUIRED. "
                f"Valid examples: {', '.join(VALID_EXCHANGES[:5])}..."
            ),
            min_length=2,
            max_length=30,
        ),
    ],
    provider: Annotated[
        str,
        Field(
            description=(
                f"Filter news by provider. Options: {', '.join(VALID_NEWS_PROVIDERS[:5])}... "
                "or 'all' for all available providers."
            ),
            min_length=3,
            max_length=20,
        ),
    ] = "all",
    area: Annotated[
        Literal["world", "americas", "europe", "asia", "oceania", "africa"],
        Field(description="Geographical region filter for news. Use 'world' for global coverage."),
    ] = "world",
    start_datetime: Annotated[
        Optional[str],
        Field(
            description=(
                "Return news published AFTER this date-time. "
                "Format: 'DD-MM-YYYY HH:MM' in IST (Indian Standard Time)."
            ),
        ),
    ] = None,
    end_datetime: Annotated[
        Optional[str],
        Field(
            description=(
                "Return news published BEFORE this date-time. "
                "Format: 'DD-MM-YYYY HH:MM' in IST (Indian Standard Time)."
            ),
        ),
    ] = None,
) -> str:
    """
    Scrape real-time news headlines from TradingView. 
    Use this to identify recent events affecting a specific symbol. 
    Returns 'storyPath' which must be used with 'get_news_content' to read full articles.
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
            return serialize_success({
                "message": f"No news headlines found for {exchange}:{symbol} in the specified range.",
                "headlines": []
            })
        return serialize_success({
            "message": f"Successfully found {len(headlines)} news articles for {exchange}:{symbol}.",
            "headlines": headlines
        })
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
