"""
Tests for NSE expiry date validation in options service.
"""

import pytest
from unittest.mock import patch, MagicMock
from tv_mcp.services.options import (
    fetch_nse_valid_expiry_dates,
    validate_nse_expiry_date,
    fetch_nse_option_chain_oi
)


class TestFetchNSEValidExpiryDates:
    """Test fetching valid expiry dates from NSE API."""

    MOCK_VALID_DATES = [
        "24-Feb-2026",
        "02-Mar-2026",
        "10-Mar-2026",
        "17-Mar-2026",
        "24-Mar-2026",
    ]

    @patch('requests.Session.get')
    def test_fetch_valid_expiry_dates_success(self, mock_get):
        """Test successfully fetching valid expiry dates."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "expiryDates": self.MOCK_VALID_DATES,
            "strikePrice": []
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_nse_valid_expiry_dates("NIFTY")

        assert result["success"] is True
        assert result["expiryDates"] == self.MOCK_VALID_DATES

    @patch('requests.Session.get')
    def test_fetch_valid_expiry_dates_for_banknifty(self, mock_get):
        """Test fetching valid expiry dates for BANKNIFTY."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "expiryDates": ["24-Feb-2026", "02-Mar-2026"],
            "strikePrice": []
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_nse_valid_expiry_dates("BANKNIFTY")

        assert result["success"] is True
        assert "24-Feb-2026" in result["expiryDates"]

    def test_fetch_valid_expiry_dates_unsupported_symbol(self):
        """Test that unsupported symbols return error."""
        result = fetch_nse_valid_expiry_dates("INVALID_SYMBOL")

        assert result["success"] is False
        assert "not supported" in result["error"]
        assert "NIFTY" in result["error"]

    @patch('requests.Session.get')
    def test_fetch_valid_expiry_dates_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_get.side_effect = Exception("Network error")

        result = fetch_nse_valid_expiry_dates("NIFTY")

        assert result["success"] is False
        assert "Failed to fetch" in result["error"]

    @patch('requests.Session.get')
    def test_fetch_valid_expiry_dates_empty_response(self, mock_get):
        """Test handling of empty expiry dates response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "expiryDates": [],
            "strikePrice": []
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_nse_valid_expiry_dates("NIFTY")

        assert result["success"] is False
        assert "No expiry dates found" in result["error"]


class TestValidateNSEExpiryDate:
    """Test expiry date validation logic."""

    MOCK_VALID_DATES = [
        "24-Feb-2026",
        "02-Mar-2026",
        "10-Mar-2026",
        "17-Mar-2026",
        "24-Mar-2026",
    ]

    @patch('tv_mcp.services.options.fetch_nse_valid_expiry_dates')
    def test_valid_expiry_date(self, mock_fetch):
        """Test validation with valid expiry date."""
        mock_fetch.return_value = {
            "success": True,
            "expiryDates": self.MOCK_VALID_DATES
        }

        result = validate_nse_expiry_date("NIFTY", "24-Feb-2026")

        assert result["success"] is True
        assert result["valid"] is True
        assert result["date"] == "24-Feb-2026"

    @patch('tv_mcp.services.options.fetch_nse_valid_expiry_dates')
    def test_invalid_expiry_date(self, mock_fetch):
        """Test validation with invalid expiry date."""
        mock_fetch.return_value = {
            "success": True,
            "expiryDates": self.MOCK_VALID_DATES
        }

        result = validate_nse_expiry_date("NIFTY", "01-Feb-2026")

        assert result["success"] is False
        assert result["valid"] is False
        assert result["provided_date"] == "01-Feb-2026"
        assert result["valid_dates"] == self.MOCK_VALID_DATES
        assert "Invalid expiry date" in result["error"]

    @patch('tv_mcp.services.options.fetch_nse_valid_expiry_dates')
    def test_invalid_expiry_date_includes_valid_options(self, mock_fetch):
        """Test that invalid date response includes list of valid dates."""
        mock_fetch.return_value = {
            "success": True,
            "expiryDates": self.MOCK_VALID_DATES
        }

        result = validate_nse_expiry_date("NIFTY", "99-Dec-2025")

        assert result["success"] is False
        assert result["valid"] is False
        assert len(result["valid_dates"]) == len(self.MOCK_VALID_DATES)
        assert "24-Feb-2026" in result["valid_dates"]

    @patch('tv_mcp.services.options.fetch_nse_valid_expiry_dates')
    def test_validation_with_api_error(self, mock_fetch):
        """Test validation when API fetch fails."""
        mock_fetch.return_value = {
            "success": False,
            "error": "Failed to fetch valid dates"
        }

        result = validate_nse_expiry_date("NIFTY", "24-Feb-2026")

        assert result["success"] is False
        assert result["valid"] is False
        assert "Failed to fetch" in result["error"]

    @patch('tv_mcp.services.options.fetch_nse_valid_expiry_dates')
    def test_validation_for_different_symbols(self, mock_fetch):
        """Test validation for different NSE symbols."""
        banknifty_dates = ["24-Feb-2026", "02-Mar-2026"]
        mock_fetch.return_value = {
            "success": True,
            "expiryDates": banknifty_dates
        }

        result = validate_nse_expiry_date("BANKNIFTY", "24-Feb-2026")

        assert result["success"] is True
        assert result["valid"] is True
        mock_fetch.assert_called_once_with("BANKNIFTY")


class TestFetchNSEOptionChainOIWithValidation:
    """Test OI fetch with integrated expiry date validation."""

    MOCK_VALID_DATES = [
        "24-Feb-2026",
        "02-Mar-2026",
        "10-Mar-2026",
    ]

    @patch('tv_mcp.services.options.validate_nse_expiry_date')
    @patch('requests.Session.get')
    def test_fetch_oi_with_valid_date(self, mock_get, mock_validate):
        """Test OI fetch with valid expiry date."""
        mock_validate.return_value = {
            "success": True,
            "valid": True,
            "date": "24-Feb-2026"
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "filtered": {
                "data": [],
                "CE": {"totOI": 100},
                "PE": {"totOI": 100}
            },
            "records": {
                "underlyingValue": 20000,
                "timestamp": "2026-02-19"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_nse_option_chain_oi("NIFTY", "24-Feb-2026")

        assert result["success"] is True
        mock_validate.assert_any_call("NIFTY", "24-Feb-2026")
        assert mock_validate.call_count >= 1

    @patch('tv_mcp.services.options.validate_nse_expiry_date')
    def test_fetch_oi_with_invalid_date_returns_helpful_error(self, mock_validate):
        """Test OI fetch with invalid date returns list of valid dates."""
        mock_validate.return_value = {
            "success": False,
            "valid": False,
            "provided_date": "01-Jan-2026",
            "valid_dates": self.MOCK_VALID_DATES,
            "error": "Invalid expiry date"
        }

        result = fetch_nse_option_chain_oi("NIFTY", "01-Jan-2026")

        assert result["success"] is False
        assert "invalid" in result["message"].lower()
        # valid_dates is a separate machine-readable field, not embedded in message
        assert result["valid_dates"] == self.MOCK_VALID_DATES

    @patch('tv_mcp.services.options.validate_nse_expiry_date')
    def test_error_message_is_ai_friendly(self, mock_validate):
        """Test that error message is user-friendly for AI."""
        mock_validate.return_value = {
            "success": False,
            "valid": False,
            "provided_date": "01-Jan-2026",
            "valid_dates": ["24-Feb-2026", "02-Mar-2026"],
            "error": "Invalid expiry date"
        }

        result = fetch_nse_option_chain_oi("NIFTY", "01-Jan-2026")

        message = result["message"]
        # Short, clean message — no emoji, no embedded date lists
        assert "❌" not in message
        assert "invalid" in message.lower()
        # Dates are cleanly separated into valid_dates
        assert result["valid_dates"] == ["24-Feb-2026", "02-Mar-2026"]

    def test_unsupported_symbol_raises_error(self):
        """Test that unsupported symbols raise ValidationError."""
        from tv_mcp.core.validators import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            fetch_nse_option_chain_oi("INVALID", "24-Feb-2026")

        assert "not supported" in str(exc_info.value)

    @patch('tv_mcp.services.options.validate_nse_expiry_date')
    @patch('requests.Session.get')
    def test_fetch_oi_with_banknifty(self, mock_get, mock_validate):
        """Test OI fetch for BANKNIFTY symbol."""
        mock_validate.return_value = {
            "success": True,
            "valid": True,
            "date": "24-Feb-2026"
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "filtered": {
                "data": [],
                "CE": {"totOI": 50000},
                "PE": {"totOI": 50000}
            },
            "records": {
                "underlyingValue": 50000,
                "timestamp": "2026-02-19"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_nse_option_chain_oi("BANKNIFTY", "24-Feb-2026")

        assert result["success"] is True
        assert result["symbol"] == "BANKNIFTY"


class TestExpiryDateFormatValidation:
    """Test expiry date format validation."""

    @patch('tv_mcp.services.options.validate_nse_expiry_date')
    def test_accepts_dd_mmm_yyyy_format(self, mock_validate):
        """Test that DD-MMM-YYYY format is accepted."""
        mock_validate.return_value = {
            "success": True,
            "valid": True,
        }

        # Valid formats
        valid_dates = [
            "24-Feb-2026",
            "02-Mar-2026",
            "10-Apr-2026",
            "31-Dec-2026"
        ]

        for date in valid_dates:
            fetch_nse_option_chain_oi("NIFTY", date)
            mock_validate.assert_called_with("NIFTY", date)

    @patch('tv_mcp.services.options.validate_nse_expiry_date')
    def test_rejects_incorrect_formats(self, mock_validate):
        """Test that incorrect date formats are handled."""
        mock_validate.return_value = {
            "success": False,
            "valid": False,
            "valid_dates": ["24-Feb-2026"]
        }

        # These should be validated by NSE
        invalid_formats = [
            "2026-02-24",  # YYYY-MM-DD
            "02/24/2026",  # MM/DD/YYYY
            "24/2/26",     # DD/MM/YY
        ]

        for invalid_date in invalid_formats:
            result = fetch_nse_option_chain_oi("NIFTY", invalid_date)
            assert result["success"] is False


class TestIntegrationScenarios:
    """Integration test scenarios for expiry date validation."""

    @patch('tv_mcp.services.options.fetch_nse_valid_expiry_dates')
    def test_real_world_date_validation_flow(self, mock_fetch):
        """Test realistic user interaction flow."""
        # User provides wrong date
        mock_fetch.return_value = {
            "success": True,
            "expiryDates": [
                "24-Feb-2026",
                "02-Mar-2026",
                "10-Mar-2026",
                "17-Mar-2026",
                "24-Mar-2026",
            ]
        }

        # User mistakenly tries invalid date
        result = validate_nse_expiry_date("NIFTY", "01-Feb-2026")

        assert result["valid"] is False
        assert len(result["valid_dates"]) > 0
        # AI can now suggest correct date
        assert "24-Feb-2026" in result["valid_dates"]

    @patch('tv_mcp.services.options.fetch_nse_valid_expiry_dates')
    @patch('requests.Session.get')
    def test_complete_workflow_with_correction(self, mock_get, mock_fetch):
        """Test complete workflow: invalid -> get valid dates -> retry with valid date."""
        mock_fetch.return_value = {
            "success": True,
            "expiryDates": ["24-Feb-2026", "02-Mar-2026"]
        }

        # First attempt with invalid date
        result1 = validate_nse_expiry_date("NIFTY", "01-Jan-2026")
        assert result1["valid"] is False
        valid_dates = result1["valid_dates"]

        # Second attempt with corrected date
        mock_fetch.return_value = {
            "success": True,
            "expiryDates": valid_dates
        }

        result2 = validate_nse_expiry_date("NIFTY", valid_dates[0])
        assert result2["valid"] is True
        assert result2["date"] == valid_dates[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
