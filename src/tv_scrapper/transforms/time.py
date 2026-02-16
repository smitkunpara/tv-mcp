"""
Timestamp and timezone conversion utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pytz


def convert_timestamp_to_indian_time(timestamp: float) -> str:
    """Convert Unix timestamp to Indian date/time in 12-hour format.

    Args:
        timestamp: Unix timestamp.

    Returns:
        Formatted IST string: ``DD-MM-YYYY HH:MM:SS AM/PM IST``
    """
    utc_dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    ist = pytz.timezone("Asia/Kolkata")
    indian_dt = utc_dt.astimezone(ist)
    return indian_dt.strftime("%d-%m-%Y %I:%M:%S %p IST")


# ── Shared IST date parsing ────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
IST_FORMATS = ["%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"]


def parse_ist_datetime_to_ts(value: str) -> Optional[float]:
    """Parse an IST-formatted datetime string into a Unix timestamp.

    Tries multiple formats (DD-MM-YYYY HH:MM, DD-MM-YYYY HH:MM:SS, DD-MM-YYYY).
    Returns ``None`` if *value* is falsy or no format matches.
    """
    if not value:
        return None
    for fmt in IST_FORMATS:
        try:
            dt_obj = datetime.strptime(value, fmt)
            return dt_obj.replace(tzinfo=IST).timestamp()
        except ValueError:
            continue
    return None


def parse_ist_datetime(value: str) -> Optional[datetime]:
    """Parse an IST-formatted datetime string into a naive datetime.

    Same format logic as ``parse_ist_datetime_to_ts`` but returns a
    ``datetime`` object (without tzinfo) for downstream comparison.
    Returns ``None`` if *value* is falsy or no format matches.
    """
    if not value:
        return None
    for fmt in IST_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
