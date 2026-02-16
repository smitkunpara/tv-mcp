"""
Unit tests for src.tv_mcp.services.options
(fetch_option_chain_data, get_current_spot_price, process_option_chain_with_analysis).

All external calls (requests.post) are mocked — no network access.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.tv_mcp.services.options import (
    _fetch_chain_native,
    _fetch_spot_price_native,
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


# ── _fetch_chain_native ──────────────────────────────────────────


class TestFetchChainNative:
    """Tests for the native tv_scraper Options API integration."""

    @patch("src.tv_mcp.services.options._HAS_NATIVE_OPTIONS", False)
    def test_returns_failure_when_native_unavailable(self):
        result = _fetch_chain_native("NIFTY", "NSE")

        assert result["success"] is False
        assert "not available" in result["message"]
        assert result["data"] is None

    @patch("src.tv_mcp.services.options._HAS_NATIVE_OPTIONS", True)
    @patch("src.tv_mcp.services.options._NativeOptions")
    def test_successful_fetch_with_expiry(self, mock_options_cls: MagicMock):
        mock_scraper = MagicMock()
        mock_options_cls.return_value = mock_scraper
        mock_scraper.get_chain_by_expiry.return_value = {
            "status": "success",
            "data": [
                {
                    "ask": 150, "bid": 140, "currency": "INR", "delta": 0.6,
                    "expiration": 20260220, "gamma": 0.01, "iv": 0.18,
                    "option-type": "call", "pricescale": 100, "rho": 0.05,
                    "root": "NIFTY", "strike": 24400, "theoPrice": 155,
                    "theta": -5.2, "vega": 12.3, "bid_iv": 0.17, "ask_iv": 0.19,
                },
            ],
            "metadata": {},
            "error": None,
        }

        result = _fetch_chain_native("NIFTY", "NSE", expiry_date=20260220)

        assert result["success"] is True
        assert result["total_count"] == 1
        assert len(result["data"]["symbols"]) == 1
        assert result["data"]["fields"] == [
            "ask", "bid", "currency", "delta", "expiration", "gamma",
            "iv", "option-type", "pricescale", "rho", "root", "strike",
            "theoPrice", "theta", "vega", "bid_iv", "ask_iv",
        ]
        sym = result["data"]["symbols"][0]
        assert "NIFTY" in sym["s"]
        assert "C" in sym["s"]  # call
        assert sym["f"][0] == 150  # ask

        # Verify expiration was passed
        call_kwargs = mock_scraper.get_chain_by_expiry.call_args
        assert call_kwargs.kwargs["expiration"] == 20260220

    @patch("src.tv_mcp.services.options._HAS_NATIVE_OPTIONS", True)
    @patch("src.tv_mcp.services.options._NativeOptions")
    def test_fetch_without_expiry_omits_param(self, mock_options_cls: MagicMock):
        mock_scraper = MagicMock()
        mock_options_cls.return_value = mock_scraper
        mock_scraper.get_chain_by_expiry.return_value = {
            "status": "success",
            "data": [],
            "metadata": {},
            "error": None,
        }

        result = _fetch_chain_native("NIFTY", "NSE")

        assert result["success"] is True
        call_kwargs = mock_scraper.get_chain_by_expiry.call_args.kwargs
        assert "expiration" not in call_kwargs

    @patch("src.tv_mcp.services.options._HAS_NATIVE_OPTIONS", True)
    @patch("src.tv_mcp.services.options._NativeOptions")
    def test_native_api_error_returns_failure(self, mock_options_cls: MagicMock):
        mock_scraper = MagicMock()
        mock_options_cls.return_value = mock_scraper
        mock_scraper.get_chain_by_expiry.return_value = {
            "status": "error",
            "data": [],
            "metadata": {},
            "error": "Symbol not found",
        }

        result = _fetch_chain_native("INVALID", "NSE")

        assert result["success"] is False
        assert "Symbol not found" in result["message"]

    @patch("src.tv_mcp.services.options._HAS_NATIVE_OPTIONS", True)
    @patch("src.tv_mcp.services.options._NativeOptions")
    def test_native_exception_returns_failure(self, mock_options_cls: MagicMock):
        mock_scraper = MagicMock()
        mock_options_cls.return_value = mock_scraper
        mock_scraper.get_chain_by_expiry.side_effect = RuntimeError("connection failed")

        result = _fetch_chain_native("NIFTY", "NSE", expiry_date=20260220)

        assert result["success"] is False
        assert "connection failed" in result["message"]

    @patch("src.tv_mcp.services.options._HAS_NATIVE_OPTIONS", True)
    @patch("src.tv_mcp.services.options._NativeOptions")
    def test_multiple_rows_converted(self, mock_options_cls: MagicMock):
        mock_scraper = MagicMock()
        mock_options_cls.return_value = mock_scraper
        mock_scraper.get_chain_by_expiry.return_value = {
            "status": "success",
            "data": [
                {
                    "ask": 150, "bid": 140, "currency": "INR", "delta": 0.6,
                    "expiration": 20260220, "gamma": 0.01, "iv": 0.18,
                    "option-type": "call", "pricescale": 100, "rho": 0.05,
                    "root": "NIFTY", "strike": 24400, "theoPrice": 155,
                    "theta": -5.2, "vega": 12.3, "bid_iv": 0.17, "ask_iv": 0.19,
                },
                {
                    "ask": 160, "bid": 150, "currency": "INR", "delta": -0.4,
                    "expiration": 20260220, "gamma": 0.01, "iv": 0.20,
                    "option-type": "put", "pricescale": 100, "rho": -0.03,
                    "root": "NIFTY", "strike": 24600, "theoPrice": 165,
                    "theta": -4.8, "vega": 11.5, "bid_iv": 0.19, "ask_iv": 0.21,
                },
            ],
            "metadata": {},
            "error": None,
        }

        result = _fetch_chain_native("NIFTY", "NSE", expiry_date=20260220)

        assert result["success"] is True
        assert result["total_count"] == 2
        symbols = result["data"]["symbols"]
        # First should be call, second put
        assert "C" in symbols[0]["s"]
        assert "P" in symbols[1]["s"]


# ── _fetch_spot_price_native ─────────────────────────────────────


class TestFetchSpotPriceNative:
    """Tests that _fetch_spot_price_native delegates to get_current_spot_price."""

    @patch("src.tv_mcp.services.options.requests.post")
    def test_delegates_to_legacy(self, mock_post: MagicMock):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "symbols": [{"s": "NSE:NIFTY", "f": [24500.50, 100]}],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = _fetch_spot_price_native("NIFTY", "NSE")

        assert result["success"] is True
        assert result["spot_price"] == 24500.50


# ── Fallback behaviour ──────────────────────────────────────────


class TestFallbackBehavior:
    """Verify process_option_chain_with_analysis tries native then legacy."""

    @patch("src.tv_mcp.services.options.fetch_option_chain_data")
    @patch("src.tv_mcp.services.options._fetch_chain_native")
    @patch("src.tv_mcp.services.options.get_current_spot_price")
    def test_falls_back_to_legacy_when_native_fails(
        self, mock_spot: MagicMock, mock_native: MagicMock, mock_legacy: MagicMock,
    ):
        mock_spot.return_value = {
            "success": True,
            "spot_price": 24500.0,
            "pricescale": 100,
        }
        mock_native.return_value = {
            "success": False,
            "message": "Native Options API not available",
            "data": None,
        }
        mock_legacy.return_value = {
            "success": True,
            "data": {
                "fields": [
                    "ask", "bid", "currency", "delta", "expiration", "gamma",
                    "iv", "option-type", "pricescale", "rho", "root", "strike",
                    "theoPrice", "theta", "vega", "bid_iv", "ask_iv",
                ],
                "symbols": [
                    {
                        "s": "NSE:NIFTY20260220C24400",
                        "f": [150, 140, "INR", 0.6, 20260220, 0.01, 0.18,
                              "call", 100, 0.05, "NIFTY", 24400, 155, -5.2,
                              12.3, 0.17, 0.19],
                    },
                ],
            },
            "total_count": 1,
        }

        result = process_option_chain_with_analysis("NIFTY", "NSE")

        mock_native.assert_called_once()
        mock_legacy.assert_called_once()
        assert result["success"] is True

    @patch("src.tv_mcp.services.options.fetch_option_chain_data")
    @patch("src.tv_mcp.services.options._fetch_chain_native")
    @patch("src.tv_mcp.services.options.get_current_spot_price")
    def test_uses_native_when_available(
        self, mock_spot: MagicMock, mock_native: MagicMock, mock_legacy: MagicMock,
    ):
        mock_spot.return_value = {
            "success": True,
            "spot_price": 24500.0,
            "pricescale": 100,
        }
        mock_native.return_value = {
            "success": True,
            "data": {
                "fields": [
                    "ask", "bid", "currency", "delta", "expiration", "gamma",
                    "iv", "option-type", "pricescale", "rho", "root", "strike",
                    "theoPrice", "theta", "vega", "bid_iv", "ask_iv",
                ],
                "symbols": [
                    {
                        "s": "NSE:NIFTY20260220C24400",
                        "f": [150, 140, "INR", 0.6, 20260220, 0.01, 0.18,
                              "call", 100, 0.05, "NIFTY", 24400, 155, -5.2,
                              12.3, 0.17, 0.19],
                    },
                ],
            },
            "total_count": 1,
        }

        result = process_option_chain_with_analysis("NIFTY", "NSE")

        mock_native.assert_called_once()
        mock_legacy.assert_not_called()
        assert result["success"] is True
