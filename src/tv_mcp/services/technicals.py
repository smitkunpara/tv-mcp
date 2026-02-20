"""
Technicals service using tv_scraper.
"""

from typing import Any, Dict
from tv_scraper import Technicals
from tv_mcp.core.validators import validate_exchange, validate_symbol, validate_timeframe


def fetch_all_indicators(
    exchange: str,
    symbol: str,
    timeframe: str,
) -> Dict[str, Any]:
    exchange = validate_exchange(exchange)
    symbol = validate_symbol(symbol)
    timeframe = validate_timeframe(timeframe)

    scraper = Technicals(export_result=False)
    try:
        result = scraper.get_data(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
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

