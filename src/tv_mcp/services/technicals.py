"""
All-indicators snapshot service.

Extracted from legacy tradingview_tools.fetch_all_indicators().
"""

from typing import Any, Dict
import contextlib
import io

from tv_scraper import Technicals  # type: ignore[import-not-found]

from ..core.validators import (
    validate_exchange,
    validate_symbol,
    validate_timeframe,
)


def fetch_all_indicators(
    exchange: str,
    symbol: str,
    timeframe: str,
) -> Dict[str, Any]:
    exchange = validate_exchange(exchange)
    symbol = validate_symbol(symbol)
    timeframe = validate_timeframe(timeframe)

    try:
        indicators_scraper = Technicals(
            export_result=False,
            export_type="json",
        )

        # Capture stdout to prevent print statements from corrupting JSON
        with contextlib.redirect_stdout(io.StringIO()):
            # Request all indicators (current snapshot)
            raw = indicators_scraper.scrape(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                all_indicators=True,
            )

        # The scraper typically returns a dict with 'status' and 'data'.
        if isinstance(raw, dict) and raw.get("status") in ("success", True):
            return {"success": True, "data": raw.get("data", {})}

        # Fallback: return raw payload if format unexpected
        return {
            "success": False,
            "message": f"Unexpected response from Indicators scraper: {type(raw)}",
            "raw": raw,
        }

    except Exception as e:
        return {"success": False, "message": f"Failed to fetch indicators: {str(e)}"}
