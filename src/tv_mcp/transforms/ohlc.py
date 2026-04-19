"""
OHLC + indicator merge logic.
"""

from typing import Any, Dict, List

from tv_mcp.core.validators import INDICATOR_MAPPING, INDICATOR_FIELD_MAPPING
from tv_mcp.transforms.time import convert_timestamp_to_indian_time


def merge_ohlc_with_indicators(data: Dict) -> List[Dict[str, Any]]:
    """Merge OHLC data with technical indicator arrays by matching timestamps.

    Creates a unified structure with indicator values embedded in OHLC records.

    Args:
        data: Dict with ``ohlc`` list and ``indicator`` dict.

    Returns:
        List of merged candle dicts.  If merge warnings exist, the final element
        will be ``{"_merge_errors": [...]}``.

    Raises:
        ValueError: If no OHLC data is present.
    """
    ohlc_data = data.get("ohlc", [])
    indicator_data = data.get("indicator", {})

    if not ohlc_data:
        raise ValueError(
            "No OHLC data found in response from TradingView. "
            "Please verify your TradingView cookie/session and parameters."
        )

    # Collect available indicators keyed by short name
    available_indicators: Dict[str, list] = {}
    for indicator_short, (indicator_key, _) in INDICATOR_MAPPING.items():
        for ind_name, ind_values in indicator_data.items():
            if indicator_key == ind_name:
                available_indicators[indicator_short] = list(ind_values)
                break

    if not available_indicators:
        merged_data = []
        for ohlc_entry in ohlc_data:
            datetime_ist = convert_timestamp_to_indian_time(
                ohlc_entry.get("timestamp")
            )
            merged_data.append(
                {
                    "open": ohlc_entry.get("open"),
                    "high": ohlc_entry.get("high"),
                    "low": ohlc_entry.get("low"),
                    "close": ohlc_entry.get("close"),
                    "volume": ohlc_entry.get("volume"),
                    "index": ohlc_entry.get("index"),
                    "datetime_ist": datetime_ist,
                }
            )
        return merged_data

    # Build per-indicator timestamp → entry maps
    indicator_maps: Dict[str, Dict[float, dict]] = {}
    for indicator_short, indicator_values in available_indicators.items():
        ts_map: Dict[float, dict] = {}
        for item in indicator_values:
            ts = item.get("timestamp")
            if ts is not None and ts not in ts_map:
                ts_map[ts] = item
        indicator_maps[indicator_short] = ts_map

    merged_data: List[Dict[str, Any]] = []
    errors: List[str] = []

    for i, ohlc_entry in enumerate(ohlc_data):
        ohlc_timestamp = ohlc_entry.get("timestamp")
        datetime_ist = convert_timestamp_to_indian_time(ohlc_timestamp)

        merged_entry: Dict[str, Any] = {
            "open": ohlc_entry.get("open"),
            "high": ohlc_entry.get("high"),
            "low": ohlc_entry.get("low"),
            "close": ohlc_entry.get("close"),
            "volume": ohlc_entry.get("volume"),
            "index": ohlc_entry.get("index"),
            "datetime_ist": datetime_ist,
        }

        for indicator_short, ts_map in indicator_maps.items():
            indicator_entry = ts_map.get(ohlc_timestamp)
            if indicator_entry is None:
                errors.append(
                    f"Indicator '{indicator_short}' missing for OHLC timestamp "
                    f"{ohlc_timestamp} (index {i})"
                )
                continue

            field_mapping = INDICATOR_FIELD_MAPPING.get(indicator_short, {})
            for index_key, field_name in field_mapping.items():
                merged_entry[field_name] = indicator_entry.get(index_key)

        merged_data.append(merged_entry)

    if errors:
        merged_data.append({"_merge_errors": errors})

    return merged_data
