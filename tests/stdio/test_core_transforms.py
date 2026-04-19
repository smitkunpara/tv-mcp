"""
Tests for tv_mcp.transforms.ohlc.
"""

import pytest
from tv_mcp.transforms.ohlc import (
    convert_timestamp_to_indian_time,
    merge_ohlc_with_indicators,
)


class TestConvertTimestamp:
    def test_known_timestamp(self):
        ts = 1707648000
        result = convert_timestamp_to_indian_time(ts)
        assert isinstance(result, str)
        assert "2024" in result


class TestMergeOhlc:
    def _sample_data(self):
        return {
            "ohlc": [
                {"timestamp": 100, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "index": 0},
            ],
            "indicator": {},
        }

    def test_no_indicators(self):
        data = self._sample_data()
        result = merge_ohlc_with_indicators(data)
        assert isinstance(result, list)
        assert len(result) == 1
        assert "close" in result[0]

    def test_empty_ohlc_raises(self):
        with pytest.raises(ValueError):
            merge_ohlc_with_indicators({"ohlc": [], "indicator": {}})
