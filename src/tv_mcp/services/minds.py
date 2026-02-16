"""
Community discussions (Minds) service.

Extracted from legacy tradingview_tools.fetch_minds().
"""

from datetime import datetime as dt
from typing import Any, Dict, Optional
import contextlib
import io

try:
    from tv_scraper import Minds  # type: ignore[import-not-found]
except ImportError:
    from tradingview_scraper.symbols.minds import Minds  # type: ignore[import-not-found]

from ..core.validators import (
    validate_exchange,
    validate_symbol,
    ValidationError,
)
from ..transforms.time import parse_ist_datetime


def fetch_minds(
    symbol: str,
    exchange: str,
    limit: Optional[int] = None,
    cookie: Optional[str] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
) -> Dict[str, Any]:
    exchange = validate_exchange(exchange)
    symbol = validate_symbol(symbol)

    # Parse date filters using shared IST parsing
    start_dt = parse_ist_datetime(start_datetime) if start_datetime else None
    end_dt = parse_ist_datetime(end_datetime) if end_datetime else None

    if start_datetime and start_dt is None:
        raise ValidationError(
            f"Invalid start_datetime format: {start_datetime}. "
            "Use IST format: DD-MM-YYYY HH:MM (e.g., '11-02-2026 09:00')"
        )
    if end_datetime and end_dt is None:
        raise ValidationError(
            f"Invalid end_datetime format: {end_datetime}. "
            "Use IST format: DD-MM-YYYY HH:MM (e.g., '11-02-2026 18:00')"
        )

    if limit is not None:
        try:
            limit = int(limit)
            if limit <= 0:
                raise ValidationError(f"limit must be a positive integer. Got: {limit}")
        except (ValueError, TypeError):
            raise ValidationError(
                f"limit must be a valid positive integer or string that can be converted to integer. Got: {limit}"
            )

    try:
        minds_scraper = Minds(export_result=False, export_type="json")

        full_symbol = f"{exchange}:{symbol}"

        with contextlib.redirect_stdout(io.StringIO()):
            discussions = minds_scraper.get_minds(symbol=full_symbol, limit=limit)

        if discussions.get("status") == "failed":
            return {
                "success": False,
                "message": discussions.get(
                    "error", "Failed to fetch minds discussions"
                ),
                "suggestion": "Please verify the symbol and exchange.",
            }

        # Apply date filtering on discussion data
        if (start_dt or end_dt) and discussions.get("data"):
            filtered_data = []
            for item in discussions["data"]:
                timestamp = (
                    item.get("timestamp", "")
                    or item.get("published", "")
                    or item.get("created", "")
                )
                if timestamp:
                    try:
                        pub_dt = None
                        for fmt in [
                            "%Y-%m-%dT%H:%M:%S",
                            "%Y-%m-%dT%H:%M:%SZ",
                            "%Y-%m-%d %H:%M:%S",
                            "%b %d, %Y %H:%M",
                            "%d %b %Y %H:%M",
                        ]:
                            try:
                                pub_dt = dt.strptime(timestamp, fmt)
                                break
                            except ValueError:
                                continue

                        if pub_dt:
                            if start_dt and pub_dt < start_dt:
                                continue
                            if end_dt and pub_dt > end_dt:
                                continue
                    except Exception:
                        pass  # If can't parse, include the item
                filtered_data.append(item)
            discussions["data"] = filtered_data
            discussions["total"] = len(filtered_data)

        # Return with success flag
        return {"success": True, **discussions}

    except ValidationError:
        raise
    except Exception as e:
        return {
            "success": False,
            "status": "failed",
            "data": [],
            "total": 0,
            "message": f"Failed to fetch minds discussions: {str(e)}",
        }
