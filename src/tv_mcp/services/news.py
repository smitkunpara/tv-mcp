"""
News service using tv_scraper.
"""

from typing import Any, Dict, List, Optional
from tv_scraper import News
from ..core.validators import (
    validate_symbol,
    validate_exchange,
    validate_news_provider,
    validate_area,
    validate_story_paths,
)
from ..core.settings import settings
from ..transforms.time import parse_ist_datetime_to_ts


def fetch_news_headlines(
    symbol: str,
    exchange: str,
    provider: str = "all",
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
        export_result=False,
        cookie=cookie or settings.TRADINGVIEW_COOKIE,
    )

    result = scraper.scrape_headlines(
        symbol=symbol,
        exchange=validated_exchange,
        provider=provider_param,
        area=area_param,
        sort_by="latest",
    )

    if result.get("status") == "success":
        headlines = result.get("data", [])
        
        # Apply local IST filtering
        if start_ts or end_ts:
            filtered = []
            for h in headlines:
                pub_ts = h.get("published")
                if pub_ts:
                    if start_ts and pub_ts < start_ts:
                        continue
                    if end_ts and pub_ts > end_ts:
                        continue
                filtered.append(h)
            return filtered
            
        return headlines
    
    raise Exception(result.get("error", "Failed to fetch news headlines. Ensure symbol and exchange are correct."))


def fetch_news_content(
    story_paths: List[str], cookie: Optional[str] = None
) -> List[Dict[str, Any]]:
    story_paths = validate_story_paths(story_paths)

    scraper = News(
        export_result=False,
        cookie=cookie or settings.TRADINGVIEW_COOKIE,
    )
    news_content: List[Dict[str, Any]] = []

    for path in story_paths:
        # tv_scraper expects story_id (which is often the path)
        result = scraper.scrape_content(story_id=path)
        
        if result.get("status") == "success":
            data = result.get("data", {})
            news_content.append({
                "success": True,
                "title": data.get("title", ""),
                "body": data.get("description", ""),
                "story_path": path,
            })
        else:
            news_content.append({
                "success": False,
                "story_path": path,
                "error": result.get("error", "Failed to fetch content"),
            })

    return news_content
