"""
News headlines and article content service.

Extracted from legacy tradingview_tools.fetch_news_headlines() and
tradingview_tools.fetch_news_content().
"""

from datetime import datetime as dt, timezone, timedelta
from typing import Any, Dict, List, Optional
import contextlib
import io

try:
    from tv_scraper import News  # type: ignore[import-not-found]
except ImportError:
    from tradingview_scraper.symbols.news import NewsScraper as News  # type: ignore[import-not-found]

from ..core.validators import (
    validate_symbol,
    validate_exchange,
    validate_news_provider,
    validate_area,
    validate_story_paths,
    ValidationError,
)
from ..core.settings import settings
from ..transforms.news import clean_for_json, extract_news_body
from ..transforms.time import parse_ist_datetime_to_ts


def fetch_news_headlines(
    symbol: str,
    exchange: Optional[str] = None,
    provider: str = "all",
    area: str = "asia",
    cookie: Optional[str] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
) -> List[Dict[str, Any]]:
    symbol = validate_symbol(symbol)
    exchange = validate_exchange(exchange) if exchange else None
    provider_param = validate_news_provider(provider)
    area = validate_area(area)

    # Parse date filters using shared IST parsing
    start_ts = parse_ist_datetime_to_ts(start_datetime) if start_datetime else None
    end_ts = parse_ist_datetime_to_ts(end_datetime) if end_datetime else None

    if start_datetime and start_ts is None:
        raise ValidationError(
            f"Invalid start_datetime format: {start_datetime}. "
            "Use IST format: DD-MM-YYYY HH:MM (e.g., '11-02-2026 09:00')"
        )

    if end_datetime and end_ts is None:
        raise ValidationError(
            f"Invalid end_datetime format: {end_datetime}. "
            "Use IST format: DD-MM-YYYY HH:MM (e.g., '11-02-2026 18:00')"
        )

    try:
        news_scraper = News(
            export_result=False,
            export_type="json",
            cookie=cookie or settings.TRADINGVIEW_COOKIE,
        )

        # Capture stdout to prevent print statements from corrupting JSON
        with contextlib.redirect_stdout(io.StringIO()):
            # Retrieve news headlines
            news_headlines = news_scraper.scrape_headlines(
                symbol=symbol,
                exchange=exchange or "",
                provider=provider_param or "",  # None for 'all'
                area=area,
                section="all",
                sort="latest",
            )

        # Clean and format headlines
        cleared_headlines: List[Dict[str, Any]] = []
        for headline in news_headlines:
            published = headline.get("published")
            pub_ts = None

            # Helper to get timestamp
            if isinstance(published, (int, float)):
                pub_ts = float(published)
            elif isinstance(published, str) and published:
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d %H:%M:%S",
                    "%b %d, %Y %H:%M",
                    "%d %b %Y %H:%M",
                ]:
                    try:
                        dt_obj = dt.strptime(published, fmt)
                        pub_ts = (
                            dt_obj.replace(tzinfo=timezone.utc).timestamp()
                            if not dt_obj.tzinfo
                            else dt_obj.timestamp()
                        )
                        break
                    except ValueError:
                        continue

            # Date filtering
            if start_ts or end_ts:
                if pub_ts is not None:
                    if start_ts and pub_ts < start_ts:
                        continue
                    if end_ts and pub_ts > end_ts:
                        continue
                else:
                    # If we can't parse date, keep it to be safe
                    pass

            cleared_headline = {
                "title": headline.get("title"),
                "published": headline.get("published"),
                "storyPath": headline.get("storyPath"),
            }
            cleared_headlines.append(cleared_headline)

        return cleared_headlines

    except Exception as e:
        raise Exception(
            f"Failed to fetch news headlines from TradingView: {str(e)}. "
            f"Please verify symbol '{symbol}' and exchange '{exchange}' are valid."
        )


def fetch_news_content(
    story_paths: List[str], cookie: Optional[str] = None
) -> List[Dict[str, Any]]:
    story_paths = validate_story_paths(story_paths)

    news_scraper = News(
        export_result=False,
        export_type="json",
        cookie=cookie or settings.TRADINGVIEW_COOKIE,
    )
    news_content: List[Dict[str, Any]] = []

    for story_path in story_paths:
        try:
            # Capture stdout to prevent print statements from corrupting JSON
            with contextlib.redirect_stdout(io.StringIO()):
                content = news_scraper.scrape_news_content(story_path=story_path)

            # Clean content for JSON serialization
            cleaned_content = clean_for_json(content)

            # Extract text body
            body = extract_news_body(cleaned_content)

            news_content.append(
                {
                    "success": True,
                    "title": cleaned_content.get("title", ""),
                    "body": body,
                    "story_path": story_path,
                }
            )

        except Exception as e:
            news_content.append(
                {
                    "success": False,
                    "title": "",
                    "body": "",
                    "story_path": story_path,
                    "error": f"Failed to fetch content: {str(e)}",
                }
            )

    return news_content
