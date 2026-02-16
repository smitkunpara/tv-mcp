"""
Unit tests for src.tv_mcp.services.options
(fetch_option_chain_data, get_current_spot_price, process_option_chain_with_analysis).

All external calls (requests.post) are mocked — no network access.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.tv_mcp.services.options import (
    fetch_option_chain_data,
    get_current_spot_price,
    process_option_chain_with_analysis,
)
from src.tv_mcp.core.validators import ValidationError


# ── fetch_option_chain_data ───────────────────────────────────────


class TestFetchOptionChainData:
    """Tests for the raw option chain fetch."""

    @patch("src.tv_mcp.services.options.requests.post")
    def test_successful_fetch(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "totalCount": 10,
            "fields": ["ask", "bid"],
            "symbols": [{"s": "NIFTY250220C24000", "f": [150, 140]}],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = fetch_option_chain_data("NIFTY", "NSE")

        assert result["success"] is True
        assert result["total_count"] == 10
        # Verify payload structure
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "columns" in payload
        assert "filter" in payload

    @patch("src.tv_mcp.services.options.requests.post")
    def test_fetch_with_expiry(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"totalCount": 5, "fields": [], "symbols": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = fetch_option_chain_data("NIFTY", "NSE", expiry_date=20260220)

        assert result["success"] is True
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        expiry_filters = [f for f in payload["filter"] if f["left"] == "expiration"]
        assert len(expiry_filters) == 1
        assert expiry_filters[0]["right"] == 20260220

    @patch("src.tv_mcp.services.options.requests.post")
    def test_handles_request_exception(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")

        result = fetch_option_chain_data("NIFTY", "NSE")

        assert result["success"] is False
        assert "Failed to fetch" in result["message"]


# ── get_current_spot_price ────────────────────────────────────────


class TestGetCurrentSpotPrice:
    """Tests for spot price retrieval."""

    @patch("src.tv_mcp.services.options.requests.post")
    def test_successful_spot_price(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "symbols": [{"s": "NSE:NIFTY", "f": [24500.50, 100]}],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = get_current_spot_price("NIFTY", "NSE")

        assert result["success"] is True
        assert result["spot_price"] == 24500.50
        assert result["pricescale"] == 100

    @patch("src.tv_mcp.services.options.requests.post")
    def test_no_price_data(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"symbols": []}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = get_current_spot_price("NIFTY", "NSE")

        assert result["success"] is False

    @patch("src.tv_mcp.services.options.requests.post")
    def test_handles_exception(self, mock_post):
        mock_post.side_effect = Exception("Timeout")

        result = get_current_spot_price("NIFTY", "NSE")

        assert result["success"] is False
        assert "Failed to fetch spot price" in result["message"]


# ── process_option_chain_with_analysis validation ─────────────────


class TestProcessOptionChainValidation:
    """Input validation for the analysis function."""

    def test_invalid_exchange_raises(self):
        with pytest.raises(ValidationError, match="Invalid exchange"):
            process_option_chain_with_analysis("NIFTY", "BAD_EX")

    def test_empty_symbol_raises(self):
        with pytest.raises(ValidationError, match="Symbol is required"):
            process_option_chain_with_analysis("", "NSE")

    def test_no_of_ITM_invalid_raises(self):
        with pytest.raises(ValidationError, match="no_of_ITM must be a valid integer"):
            process_option_chain_with_analysis("NIFTY", "NSE", no_of_ITM=object())  # type: ignore[arg-type]

    def test_no_of_ITM_zero_raises(self):
        with pytest.raises(ValidationError, match="no_of_ITM must be between 1 and 20"):
            process_option_chain_with_analysis("NIFTY", "NSE", no_of_ITM=0)

    def test_no_of_OTM_over_20_raises(self):
        with pytest.raises(ValidationError, match="no_of_OTM must be between 1 and 20"):
            process_option_chain_with_analysis("NIFTY", "NSE", no_of_OTM=21)


# ── process_option_chain_with_analysis success ───────────────────


class TestProcessOptionChainSuccess:
    """Integration of spot price + option chain with analysis."""

    @patch("src.tv_mcp.services.options.fetch_option_chain_data")
    @patch("src.tv_mcp.services.options.get_current_spot_price")
    def test_nearest_expiry_filtering(self, mock_spot, mock_chain):
        mock_spot.return_value = {
            "success": True,
            "spot_price": 24500.0,
            "pricescale": 100,
        }
        mock_chain.return_value = {
            "success": True,
            "data": {
                "fields": [
                    "ask", "bid", "currency", "delta", "expiration", "gamma",
                    "iv", "option-type", "pricescale", "rho", "root", "strike",
                    "theoPrice", "theta", "vega", "bid_iv", "ask_iv",
                ],
                "symbols": [
                    # Call option expiry 20260220, strike 24400
                    {
                        "s": "NSE:NIFTY20260220C24400",
                        "f": [150, 140, "INR", 0.6, 20260220, 0.01, 0.18,
                              "call", 100, 0.05, "NIFTY", 24400, 155, -5.2, 12.3, 0.17, 0.19],
                    },
                    # Put option expiry 20260220, strike 24600
                    {
                        "s": "NSE:NIFTY20260220P24600",
                        "f": [160, 150, "INR", -0.4, 20260220, 0.01, 0.20,
                              "put", 100, -0.03, "NIFTY", 24600, 165, -4.8, 11.5, 0.19, 0.21],
                    },
                ],
            },
            "total_count": 2,
        }

        result = process_option_chain_with_analysis(
            "NIFTY", "NSE", expiry_date="nearest", no_of_ITM=5, no_of_OTM=5,
        )

        assert result["success"] is True
        assert result["spot_price"] == 24500.0
        assert isinstance(result["data"], list)
        assert "analytics" in result

    @patch("src.tv_mcp.services.options.fetch_option_chain_data")
    @patch("src.tv_mcp.services.options.get_current_spot_price")
    def test_spot_price_failure_propagates(self, mock_spot, mock_chain):
        mock_spot.return_value = {
            "success": False,
            "message": "Could not connect",
        }

        result = process_option_chain_with_analysis("NIFTY", "NSE")

        assert result["success"] is False
        assert "spot price" in result["message"].lower()
