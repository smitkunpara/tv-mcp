"""
Live OI integration tests (no mocked API responses).

These tests hit NSE/BSE endpoints using dynamic valid expiries so they stay stable.
"""

from datetime import datetime
import pytest

from src.tv_mcp.core.validators import ValidationError
from src.tv_mcp.services.options import (
    fetch_bse_valid_expiry_dates,
    fetch_nse_valid_expiry_dates,
    fetch_option_chain_oi,
)


def _retry_result(func, *args, attempts: int = 3, **kwargs):
    last_result = None
    for _ in range(attempts):
        last_result = func(*args, **kwargs)
        if not isinstance(last_result, dict):
            return last_result
        message = (last_result.get("message") or last_result.get("error") or "").lower()
        if "timed out" in message or "timeout" in message:
            continue
        return last_result
    return last_result


def _get_iso_expiry_for(exchange: str, symbol: str) -> str:
    if exchange == "NSE":
        expiry_lookup = _retry_result(fetch_nse_valid_expiry_dates, symbol)
        assert expiry_lookup is not None and isinstance(expiry_lookup, dict)
        assert expiry_lookup.get("success") is True
        expiry_dates = expiry_lookup.get("expiryDates")
        assert isinstance(expiry_dates, list) and expiry_dates
        nse_expiry = expiry_dates[0]
        return datetime.strptime(nse_expiry, "%d-%b-%Y").strftime("%Y-%m-%d")

    expiry_lookup = _retry_result(fetch_bse_valid_expiry_dates, symbol)
    assert expiry_lookup is not None and isinstance(expiry_lookup, dict)
    if not expiry_lookup.get("success"):
        message = (expiry_lookup.get("message") or expiry_lookup.get("error") or "").lower()
        if "timed out" in message or "timeout" in message:
            pytest.skip(f"BSE live API timeout while fetching expiry for {symbol}")
    assert expiry_lookup.get("success") is True
    valid_dates = expiry_lookup.get("valid_dates")
    assert isinstance(valid_dates, list) and valid_dates
    return valid_dates[0]


def test_real_nse_oi_unified_service_live() -> None:
    """Fetch real NSE OI data via unified service using ISO expiry."""
    iso_expiry = _get_iso_expiry_for("NSE", "NIFTY")

    result = fetch_option_chain_oi(
        exchange="NSE",
        symbol="NIFTY",
        expiry_date=iso_expiry,
    )

    assert result.get("success") is True
    assert result.get("exchange") == "NSE"
    assert result.get("symbol") == "NIFTY"
    assert result.get("expiry") == iso_expiry
    assert isinstance(result.get("data"), list)
    assert isinstance(result.get("totals"), dict)

    if result["data"]:
        row = result["data"][0]
        assert "strike" in row
        assert "ce_oi" in row
        assert "pe_oi" in row
        assert "ce_oi_chg" in row
        assert "pe_oi_chg" in row


def test_real_bse_oi_unified_service_live() -> None:
    """Fetch real BSE OI data via unified service using ISO expiry."""
    iso_expiry = _get_iso_expiry_for("BSE", "SENSEX")

    result = fetch_option_chain_oi(
        exchange="BSE",
        symbol="SENSEX",
        expiry_date=iso_expiry,
    )

    assert result.get("success") is True
    assert result.get("exchange") == "BSE"
    assert result.get("symbol") == "SENSEX"
    assert result.get("expiry") == iso_expiry
    assert isinstance(result.get("data"), list)
    assert isinstance(result.get("totals"), dict)

    if result["data"]:
        row = result["data"][0]
        assert "strike" in row
        assert "ce_oi" in row
        assert "pe_oi" in row
        assert "ce_oi_chg" in row
        assert "pe_oi_chg" in row


@pytest.mark.parametrize(
    "exchange,symbol",
    [
        ("NSE", "NIFTY"),
        ("NSE", "BANKNIFTY"),
        ("BSE", "SENSEX"),
        ("BSE", "BANKEX"),
        ("BSE", "SX50"),
    ],
)
def test_real_oi_symbol_exchange_combinations_live(exchange: str, symbol: str) -> None:
    """Verify real OI fetch works for supported exchange/symbol combinations."""
    iso_expiry = _get_iso_expiry_for(exchange, symbol)

    result = _retry_result(
        fetch_option_chain_oi,
        exchange=exchange,
        symbol=symbol,
        expiry_date=iso_expiry,
    )
    assert result is not None and isinstance(result, dict)

    if not result.get("success"):
        message = (result.get("message") or result.get("error") or "").lower()
        if "timed out" in message or "timeout" in message:
            pytest.skip(f"Live API timeout for {exchange}:{symbol}")
        if "no oi data found" in message:
            pytest.skip(f"No OI data available for {exchange}:{symbol} at selected expiry {iso_expiry}")

    assert result.get("success") is True
    assert result.get("exchange") == exchange
    assert result.get("symbol") == symbol
    assert result.get("expiry") == iso_expiry


def test_invalid_exchange_symbol_mismatch_raises_validation_error() -> None:
    """Exchange/symbol mismatch should fail fast with clear validation error."""
    with pytest.raises(ValidationError):
        fetch_option_chain_oi(
            exchange="NSE",
            symbol="SENSEX",
            expiry_date="2026-03-25",
        )


def test_invalid_exchange_for_oi_raises_validation_error() -> None:
    """Unsupported exchange should raise validation error."""
    with pytest.raises(ValidationError):
        fetch_option_chain_oi(
            exchange="NASDAQ",
            symbol="NIFTY",
            expiry_date="2026-03-25",
        )


def test_invalid_iso_expiry_format_raises_validation_error() -> None:
    """Non-ISO expiry format should raise validation error."""
    with pytest.raises(ValidationError):
        fetch_option_chain_oi(
            exchange="NSE",
            symbol="NIFTY",
            expiry_date="25-Mar-2026",
        )


def test_invalid_but_iso_expiry_date_returns_valid_dates() -> None:
    """ISO date with valid format but unavailable expiry should return valid_dates."""
    result = fetch_option_chain_oi(
        exchange="BSE",
        symbol="SENSEX",
        expiry_date="2099-12-31",
    )

    assert result.get("success") is False
    assert "valid_dates" in result
    assert isinstance(result["valid_dates"], list)
    assert len(result["valid_dates"]) > 0
