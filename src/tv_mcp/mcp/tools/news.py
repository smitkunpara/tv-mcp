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
        Optional[str],
        Field(
            description=(
                "Trading symbol/ticker for news (e.g., 'AAPL', 'BTCUSD'). REQUIRED."
            ),
        ),
    ] = None,
    exchange: Annotated[
        Optional[str],
        Field(
            description=(
                "Stock exchange name where the symbol is traded (e.g., 'NASDAQ', 'BINANCE'). REQUIRED."
            ),
        ),
    ] = None,
    provider: Annotated[
        str,
        Field(
            description=(
                f"Filter news by provider. Options: {', '.join(VALID_NEWS_PROVIDERS[:5])}... "
                "or 'all' for all available providers. Default is 'all'."
            ),
        ),
    ] = "all",
    area: Annotated[
        Literal["world", "americas", "europe", "asia", "oceania", "africa"],
        Field(description="Geographical region filter for news. Default is 'world'."),
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
    """
    try:
        if not exchange:
            return serialize_error("Missing REQUIRED field: 'exchange'. Please specify the exchange (e.g., 'NASDAQ').")
        if not symbol:
            return serialize_error("Missing REQUIRED field: 'symbol'. Please specify the ticker (e.g., 'AAPL').")

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
        Optional[List[str]],
        Field(
            description=(
                "List of story paths from news headlines. REQUIRED."
            ),
        ),
    ] = None,
) -> str:
    """
    Fetch full news article content using story paths from headlines.
    """
    try:
        if not story_paths:
            return serialize_error("Missing REQUIRED field: 'story_paths'. Please provide a list of story paths (e.g., ['/news/...']). Get these from get_news_headlines().")

        articles = fetch_news_content(story_paths)
        return serialize_success({"articles": articles})
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")
