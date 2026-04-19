"""
News service using tv_scraper.
"""

from typing import Any, Dict, List, Optional
from tv_scraper import News
from tv_mcp.core.validators import (
    validate_symbol,
    validate_exchange,
    validate_news_provider,
    validate_area,
    ValidationError,
)
from tv_mcp.core.settings import settings
from tv_mcp.transforms.time import parse_ist_datetime_to_ts


def fetch_news_headlines(
    symbol: str,
    exchange: str,
    provider: Optional[str] = "all",
    area: str = "world",
    cookie: Optional[str] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch news headlines with optional IST date-time filtering."""
    symbol = validate_symbol(symbol)
    validated_exchange = validate_exchange(exchange)
    provider_param = validate_news_provider(provider)
    area_param = validate_area(area)

    start_ts = parse_ist_datetime_to_ts(start_datetime) if start_datetime else None
    end_ts = parse_ist_datetime_to_ts(end_datetime) if end_datetime else None

    scraper = News(
        export=None,
        cookie=cookie or settings.TRADINGVIEW_COOKIE,
    )

    result = scraper.get_news_headlines(
        symbol=symbol,
        exchange=validated_exchange,
        provider=provider_param,
        area=area_param,
        sort_by="latest",
    )

    if result.get("status") == "success":
        headlines = result.get("data", [])
        
        cleaned_headlines = []
        for h in headlines:
            pub_ts = h.get("published")
            
            # Filter by date if requested
            if start_ts or end_ts:
                if pub_ts:
                    if start_ts and pub_ts < start_ts:
                        continue
                    if end_ts and pub_ts > end_ts:
                        continue
            
            # Remove storyPath, keep id as the primary identifier for content fetching
            cleaned_headlines.append({
                "id": h.get("id"),
                "title": h.get("title"),
                "shortDescription": h.get("shortDescription"),
                "published": pub_ts
            })
            
        return cleaned_headlines
    
    raise Exception(result.get("error", "Failed to fetch news headlines. Ensure symbol and exchange are correct."))


def fetch_news_content(
    story_ids: List[str], cookie: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fetch full content for a list of story IDs."""
    if not story_ids:
        raise ValidationError("At least one story ID is required.")

    scraper = News(
        export=None,
        cookie=cookie or settings.TRADINGVIEW_COOKIE,
    )
    news_content: List[Dict[str, Any]] = []

    for sid in story_ids:
        result = scraper.get_news_content(story_id=sid)
        
        if result.get("status") == "success":
            data = result.get("data", {})
            news_content.append({
                "success": True,
                "title": data.get("title", ""),
                "body": data.get("description", ""),
            })
        else:
            news_content.append({
                "success": False,
                "error": result.get("error", "Failed to fetch content"),
            })

    return news_content
