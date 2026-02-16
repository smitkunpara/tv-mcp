"""
Parity tests for tv_scrapper.transforms vs legacy tradingview_mcp.utils.

Verifies that time, news, and ohlc transforms produce identical output.
"""

import pytest

# New modules
from src.tv_scrapper.transforms.time import convert_timestamp_to_indian_time as new_ts
from src.tv_scrapper.transforms.time import parse_ist_datetime_to_ts, parse_ist_datetime
from src.tv_scrapper.transforms.news import clean_for_json as new_clean
from src.tv_scrapper.transforms.news import extract_news_body as new_extract
from src.tv_scrapper.transforms.ohlc import merge_ohlc_with_indicators as new_merge

# Legacy
from src.tradingview_mcp.utils import (
    convert_timestamp_to_indian_time as old_ts,
    clean_for_json as old_clean,
    extract_news_body as old_extract,
    merge_ohlc_with_indicators as old_merge,
)


class TestTimeParity:
    """convert_timestamp_to_indian_time must return the same string."""

    def test_known_timestamp(self):
        ts = 1707648000  # 2024-02-11 12:00 UTC
        assert new_ts(ts) == old_ts(ts)

    def test_zero_timestamp(self):
        assert new_ts(0) == old_ts(0)


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


class TestCleanForJsonParity:
    def test_dict_passthrough(self):
        d = {"a": 1, "b": [2, 3]}
        assert new_clean(d) == old_clean(d)

    def test_nested_list(self):
        lst = [{"key": "val"}, 42, "text"]
        assert new_clean(lst) == old_clean(lst)


class TestExtractNewsBodyParity:
    def test_with_text_blocks(self):
        content = {
            "body": [
                {"type": "text", "content": "First paragraph."},
                {"type": "image", "src": "img.png"},
                {"type": "text", "content": "Second paragraph."},
            ]
        }
        assert new_extract(content) == old_extract(content)

    def test_empty_body(self):
        assert new_extract({}) == old_extract({})


class TestMergeOhlcParity:
    """merge_ohlc_with_indicators must produce the same output."""

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
        assert new_merge(data) == old_merge(data)

    def test_empty_ohlc_raises(self):
        with pytest.raises(ValueError):
            new_merge({"ohlc": [], "indicator": {}})
        with pytest.raises(ValueError):
            old_merge({"ohlc": [], "indicator": {}})
