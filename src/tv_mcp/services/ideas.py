"""
Community trading ideas service.

Extracted from legacy tradingview_tools.fetch_ideas().
"""

from typing import Any, Dict, Optional
import contextlib
import io

from tv_scraper import Ideas  # type: ignore[import-not-found]

from ..core.validators import (
    validate_symbol,
    validate_exchange,
    ValidationError,
)
from ..core.settings import settings
from ..transforms.time import parse_ist_datetime_to_ts


def fetch_ideas(
    symbol: str,
    exchange: str = "BITSTAMP",
    startPage: int = 1,
    endPage: int = 1,
    sort: str = "popular",
    export_type: str = "json",
    cookie: Optional[str] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
) -> Dict[str, Any]:
    symbol = validate_symbol(symbol)
    exchange = validate_exchange(exchange)

    # Convert string to int if necessary for startPage and endPage
    try:
        startPage = int(startPage)
    except (ValueError, TypeError):
        raise ValidationError(
            f"startPage must be a valid integer or string that can be converted to integer. Got: {startPage}"
        )

    try:
        endPage = int(endPage)
    except (ValueError, TypeError):
        raise ValidationError(
            f"endPage must be a valid integer or string that can be converted to integer. Got: {endPage}"
        )

    if endPage < startPage:
        raise ValidationError("endPage must be greater than or equal to startPage.")

    if sort not in ("popular", "recent"):
        raise ValidationError("sort must be either 'popular' or 'recent'.")

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
        ideas_scraper = Ideas(
            export_result=False,
            export_type=export_type,
            cookie=cookie or settings.TRADINGVIEW_COOKIE,
        )

        # Capture stdout to prevent print statements from corrupting JSON
        with contextlib.redirect_stdout(io.StringIO()):
            ideas_result = ideas_scraper.scrape(
                symbol=symbol,
                exchange=exchange,
                start_page=startPage,
                end_page=endPage,
                sort_by=sort,
            )

        # Unwrap envelope
        if ideas_result.get("status") == "failed":
            raise Exception(ideas_result.get("error", "Ideas scrape failed"))
        ideas = ideas_result.get("data", [])

        # Apply date filtering
        if (start_ts or end_ts) and ideas:
            filtered_ideas = []
            for idea in ideas:
                # idea['timestamp'] is typically a Unix timestamp (int/float)
                ts = idea.get("timestamp")
                if ts is not None:
                    try:
                        ts = float(ts)
                        if start_ts and ts < start_ts:
                            continue
                        if end_ts and ts > end_ts:
                            continue
                    except (ValueError, TypeError):
                        pass  # Keep if timestamp invalid/missing
                filtered_ideas.append(idea)
            ideas = filtered_ideas

        if ideas == []:
            return {
                "success": False,
                "message": "No ideas found for the given symbol.",
                "suggestion": "Tell user to update the cookies after solving the captcha to access ideas.",
            }
        return {"success": True, "ideas": ideas, "count": len(ideas)}

    except ValidationError:
        # Re-raise validation errors so callers can handle them consistently
        raise
    except Exception as e:
        return {
            "success": False,
            "ideas": [],
            "count": 0,
            "message": f"Failed to fetch ideas: {str(e)}",
        }
