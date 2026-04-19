"""
Technicals service using tv_scraper.
"""

from typing import Any, Dict
from tv_scraper import Technicals
from tv_mcp.core.validators import validate_exchange, validate_symbol, validate_timeframe
from tv_mcp.services._compat import build_scraper, call_first_supported_method


def fetch_all_indicators(
    exchange: str,
    symbol: str,
    timeframe: str,
) -> Dict[str, Any]:
    exchange = validate_exchange(exchange)
    symbol = validate_symbol(symbol)
    timeframe = validate_timeframe(timeframe)

    scraper = build_scraper(Technicals)
    try:
        result = call_first_supported_method(
            scraper,
            ("get_technicals", "get_data"),
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            technical_indicators=None,
            all_indicators=True,
        )

        if isinstance(result, dict) and result.get("status") == "success":
            return {"success": True, "data": result.get("data", {})}

        return {
            "success": False,
            "message": result.get("error") if isinstance(result, dict) else "Unexpected response format",
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to fetch indicators: {str(e)}"}

