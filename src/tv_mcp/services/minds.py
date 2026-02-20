"""
Minds service using tv_scraper.
"""

from typing import Any, Dict, Optional
from datetime import datetime
from tv_scraper import Minds
from tv_mcp.core.validators import validate_exchange, validate_symbol
from tv_mcp.transforms.time import parse_ist_datetime_to_ts


def fetch_minds(
    symbol: str,
    exchange: str,
    limit: Optional[int] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch community discussions with optional IST date-time filtering."""
    exchange = validate_exchange(exchange)
    symbol = validate_symbol(symbol)

    start_ts = parse_ist_datetime_to_ts(start_datetime) if start_datetime else None
    end_ts = parse_ist_datetime_to_ts(end_datetime) if end_datetime else None

    scraper = Minds(export_result=False)
    result = scraper.get_data(exchange=exchange, symbol=symbol, limit=limit)

    if result.get("status") == "success":
        data = result.get("data", [])
        
        # Apply local IST filtering
        if start_ts or end_ts:
            filtered = []
            for mind in data:
                # Minds usually have 'created' as a string like "2026-02-16 20:30:00"
                # Need to convert to ts for comparison.
                created_str = mind.get("created")
                if created_str:
                    try:
                        # tv_scraper formats it as "YYYY-MM-DD HH:MM:SS" (naive in response but originally UTC)
                        dt_obj = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
                        # Assuming the scraper's 'created' is UTC normalized by datetime.fromisoformat in Minds._parse_mind
                        # and then formatted. Let's assume it's a UTC timestamp representation.
                        import pytz
                        ts = pytz.UTC.localize(dt_obj).timestamp()
                        
                        if start_ts and ts < start_ts:
                            continue
                        if end_ts and ts > end_ts:
                            continue
                    except ValueError:
                        pass
                filtered.append(mind)
            data = filtered

        return {
            "success": True, 
            "data": data,
            "total": len(data),
            "message": f"Successfully retrieved {len(data)} community discussions for {exchange}:{symbol}. Analyze these for real-time crowd sentiment."
        }
    
    return {
        "success": False, 
        "message": f"Failed to fetch minds: {result.get('error')}. Verify that the symbol {symbol} exists on {exchange}."
    }
