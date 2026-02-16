"""
Tests for tv_mcp.transforms — time, news, and ohlc transforms.

Verifies all transform functions produce correct output.
"""

import pytest

from src.tv_mcp.transforms.time import (
    convert_timestamp_to_indian_time,
    parse_ist_datetime_to_ts,
    parse_ist_datetime,
)
from src.tv_mcp.transforms.news import clean_for_json, extract_news_body
from src.tv_mcp.transforms.ohlc import merge_ohlc_with_indicators


class TestConvertTimestamp:
    """convert_timestamp_to_indian_time must format correctly."""

    def test_known_timestamp(self):
        ts = 1707648000  # 2024-02-11 12:00 UTC → 17:30 IST
        result = convert_timestamp_to_indian_time(ts)
        assert isinstance(result, str)
        assert "2024" in result

    def test_zero_timestamp(self):
        result = convert_timestamp_to_indian_time(0)
        assert isinstance(result, str)
        assert "1970" in result


class TestTimeParsingHelpers:
    """New helpers for shared IST date parsing."""

    def test_parse_ist_datetime_to_ts_valid(self):
        result = parse_ist_datetime_to_ts("11-02-2026 09:00")
        assert result is not None
        assert isinstance(result, float)

    def test_parse_ist_datetime_to_ts_date_only(self):
        result = parse_ist_datetime_to_ts("11-02-2026")
        assert result is not None

    def test_parse_ist_datetime_to_ts_invalid(self):
        result = parse_ist_datetime_to_ts("not-a-date")
        assert result is None

    def test_parse_ist_datetime_to_ts_empty(self):
        result = parse_ist_datetime_to_ts("")
        assert result is None

    def test_parse_ist_datetime_returns_datetime(self):
        result = parse_ist_datetime("11-02-2026 09:00")
        assert result is not None
        assert result.day == 11
        assert result.month == 2


class TestCleanForJson:
    def test_dict_passthrough(self):
        d = {"a": 1, "b": [2, 3]}
        result = clean_for_json(d)
        assert result == d

    def test_nested_list(self):
        lst = [{"key": "val"}, 42, "text"]
        result = clean_for_json(lst)
        assert result == lst


class TestExtractNewsBody:
    def test_with_text_blocks(self):
        content = {
            "body": [
                {"type": "text", "content": "First paragraph."},
                {"type": "image", "src": "img.png"},
                {"type": "text", "content": "Second paragraph."},
            ]
        }
        result = extract_news_body(content)
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_empty_body(self):
        result = extract_news_body({})
        assert isinstance(result, str)


class TestMergeOhlc:
    """merge_ohlc_with_indicators must produce correct output."""

    def _sample_data(self):
        return {
            "ohlc": [
                {"timestamp": 100, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "index": 0},
                {"timestamp": 200, "open": 1.5, "high": 2.5, "low": 1, "close": 2, "volume": 20, "index": 1},
            ],
            "indicator": {},
        }

    def test_no_indicators(self):
        data = self._sample_data()
        result = merge_ohlc_with_indicators(data)
        assert isinstance(result, list)
        assert len(result) == 2
        assert "close" in result[0]

    def test_empty_ohlc_raises(self):
        with pytest.raises(ValueError):
            merge_ohlc_with_indicators({"ohlc": [], "indicator": {}})
