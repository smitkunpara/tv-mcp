"""
Ideas service using tv_scraper.
"""

from typing import Any, Dict, Optional
from tv_scraper import Ideas
from tv_mcp.core.validators import validate_symbol, validate_exchange, ValidationError
from tv_mcp.core.settings import settings
from tv_mcp.transforms.time import parse_ist_datetime_to_ts


def fetch_ideas(
    symbol: str,
    exchange: str,
    startPage: int = 1,
    endPage: int = 1,
    sort: str = "popular",
    cookie: Optional[str] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch trading ideas with optional IST date-time filtering."""
    symbol = validate_symbol(symbol)
    exchange = validate_exchange(exchange)

    start_ts = parse_ist_datetime_to_ts(start_datetime) if start_datetime else None
    end_ts = parse_ist_datetime_to_ts(end_datetime) if end_datetime else None

    try:
        scraper = Ideas(
            export_result=False,
            cookie=cookie or settings.TRADINGVIEW_COOKIE,
        )

        result = scraper.get_data(
            symbol=symbol,
            exchange=exchange,
            start_page=int(startPage),
            end_page=int(endPage),
            sort_by=sort,
        )

        if result.get("status") == "success":
            data = result.get("data", [])
            
            # Apply local IST filtering
            if start_ts or end_ts:
                filtered = []
                for idea in data:
                    ts = idea.get("timestamp")
                    if ts:
                        if start_ts and ts < start_ts:
                            continue
                        if end_ts and ts > end_ts:
                            continue
                    filtered.append(idea)
                data = filtered

            return {
                "success": True, 
                "ideas": data, 
                "count": len(data),
                "message": f"Successfully retrieved {len(data)} ideas for {exchange}:{symbol}. Use these to analyze market sentiment."
            }
        
        return {
            "success": False, 
            "message": f"Failed to fetch ideas: {result.get('error')}. Ensure your TRADINGVIEW_COOKIE is valid and not expired."
        }

    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}. Please check if {exchange}:{symbol} is a valid pair."}
