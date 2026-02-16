"""
IST Time parsing and conversion utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import pytz

IST_TZ = pytz.timezone("Asia/Kolkata")
IST_OFFSET = timezone(timedelta(hours=5, minutes=30))

def convert_timestamp_to_indian_time(timestamp: float) -> str:
    """Convert Unix timestamp to Indian date/time string."""
    utc_dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    indian_dt = utc_dt.astimezone(IST_TZ)
    return indian_dt.strftime("%d-%m-%Y %I:%M:%S %p IST")

def parse_ist_datetime_to_ts(value: str) -> Optional[float]:
    """Parse an IST-formatted datetime string into a Unix timestamp.
    
    Expected format: DD-MM-YYYY HH:MM or DD-MM-YYYY
    """
    if not value:
        return None
    
    formats = ["%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"]
    for fmt in formats:
        try:
            dt_obj = datetime.strptime(value, fmt)
            # Localize to IST then convert to UTC timestamp
            localized = IST_TZ.localize(dt_obj)
            return localized.timestamp()
        except ValueError:
            continue
    return None
