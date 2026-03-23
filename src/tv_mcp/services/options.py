"""
Options service using tv_scraper.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from tv_scraper import Options, Overview

from tv_mcp.core.validators import (
    ValidationError,
    validate_exchange,
    validate_oi_symbol,
    validate_symbol,
)

BSE_SCRIP_CODES: Dict[str, int] = {
    "SENSEX": 1,
    "BANKEX": 12,
    "SX50": 47,
}


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _parse_int(value: Any) -> Optional[int]:
    parsed = _parse_number(value)
    if parsed is None:
        return None
    return int(parsed)


def _parse_float(value: Any) -> Optional[float]:
    return _parse_number(value)


def _parse_iso_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            f"Invalid expiry_date '{date_str}'. Use ISO format YYYY-MM-DD (e.g., 2026-03-25)."
        )


def _iso_to_nse_date(iso_date: str) -> str:
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d-%b-%Y")


def _nse_to_iso_date(nse_date: str) -> Optional[str]:
    try:
        return datetime.strptime(nse_date, "%d-%b-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _bse_display_to_iso_date(display_date: str) -> Optional[str]:
    try:
        return datetime.strptime(display_date.strip(), "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _nse_timestamp_to_iso(ts: Optional[str]) -> Optional[str]:
    if not ts or not isinstance(ts, str):
        return None
    ts = ts.strip()
    formats = [
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M",
        "%d-%b-%Y",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(ts, fmt)
            return parsed.isoformat(timespec="seconds")
        except ValueError:
            continue
    return ts


def _bse_timestamp_to_iso(ts: Optional[str]) -> Optional[str]:
    if not ts or not isinstance(ts, str):
        return None
    ts = ts.strip()
    formats = [
        "%d %b %Y | %H:%M",
        "%d %b %Y",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(ts, fmt)
            return parsed.isoformat(timespec="seconds")
        except ValueError:
            continue
    return ts


def fetch_nse_valid_expiry_dates(symbol: str) -> Dict[str, Any]:
    """
    Fetch valid option expiry dates from NSE for a given symbol.

    Args:
        symbol: NSE Index symbol (e.g., 'NIFTY', 'BANKNIFTY')

    Returns:
        Dict with valid expiry dates list or error info
    """
    supported = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"]
    if symbol.upper() not in supported:
        return {
            "success": False,
            "error": f"Symbol '{symbol}' not supported for NSE OI data. Supported: {', '.join(supported)}",
        }

    url = "https://www.nseindia.com/api/option-chain-contract-info"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
    }

    params = {"symbol": symbol.upper()}

    try:
        import requests

        session = requests.Session()
        session.get(
            "https://www.nseindia.com/option-chain", headers=headers, timeout=10
        )

        response = session.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        expiry_dates = data.get("expiryDates", [])
        if not expiry_dates:
            return {"success": False, "error": f"No expiry dates found for {symbol}"}

        return {"success": True, "expiryDates": expiry_dates}

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch valid expiry dates from NSE: {str(e)}",
        }


def fetch_bse_valid_expiry_dates(symbol: str) -> Dict[str, Any]:
    symbol = symbol.upper()
    scrip_code = BSE_SCRIP_CODES.get(symbol)
    if not scrip_code:
        supported = ", ".join(BSE_SCRIP_CODES.keys())
        return {
            "success": False,
            "error": f"Symbol '{symbol}' not supported for BSE OI data. Supported: {supported}",
        }

    url = "https://api.bseindia.com/BseIndiaAPI/api/ddlExpiry_IV/w"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.bseindia.com",
        "Referer": "https://www.bseindia.com/",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        ),
    }

    try:
        import requests

        response = requests.get(
            url,
            params={"ProductType": "IO", "scrip_cd": scrip_code},
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        expiry_rows = data.get("Table1", [])
        if not expiry_rows:
            return {
                "success": False,
                "error": f"No expiry dates found for {symbol}",
            }

        expiry_map: Dict[str, str] = {}
        for row in expiry_rows:
            display = (row.get("ExpiryDate") or "").strip()
            iso = _bse_display_to_iso_date(display)
            if iso and display:
                expiry_map[iso] = display

        if not expiry_map:
            return {
                "success": False,
                "error": f"No valid expiry dates found for {symbol}",
            }

        return {
            "success": True,
            "expiry_map": expiry_map,
            "valid_dates": sorted(expiry_map.keys()),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch valid expiry dates from BSE: {str(e)}",
        }


def validate_nse_expiry_date(symbol: str, expiry_date: str) -> Dict[str, Any]:
    """
    Validate if the provided expiry date is valid for NSE options.

    Args:
        symbol: NSE Index symbol
        expiry_date: Expiry date in DD-MMM-YYYY format (e.g., '19-Feb-2026')

    Returns:
        Dict indicating validation success and available dates if invalid
    """
    # Fetch valid expiry dates
    result = fetch_nse_valid_expiry_dates(symbol)

    if not result.get("success"):
        return {"success": False, "valid": False, "error": result.get("error")}

    valid_dates = result.get("expiryDates", [])

    # Check if provided date is in the list
    if expiry_date in valid_dates:
        return {"success": True, "valid": True, "date": expiry_date}

    # Date is invalid - return helpful error
    return {
        "success": False,
        "valid": False,
        "provided_date": expiry_date,
        "valid_dates": valid_dates,
        "error": f"Invalid expiry date '{expiry_date}' for {symbol}. Please use one of the available expiry dates.",
    }


def get_current_spot_price(symbol: str, exchange: str) -> float:
    scraper = Overview(export_result=False)
    result = scraper.get_data(exchange=exchange, symbol=symbol, fields=["close"])
    if result.get("status") == "success":
        price = (result.get("data") or {}).get("close")
        if price is not None:
            return float(price)
    raise Exception(
        f"Failed to fetch spot price for {symbol}: {result.get('error', 'price unavailable or None')}"
    )


def _fetch_nse_option_chain_oi_iso(symbol: str, expiry_date_iso: str) -> Dict[str, Any]:
    expiry_date_nse = _iso_to_nse_date(expiry_date_iso)

    validation_result = validate_nse_expiry_date(symbol, expiry_date_nse)
    if not validation_result.get("valid"):
        valid_dates_raw = validation_result.get("valid_dates", [])
        valid_dates_iso = [
            iso for iso in (_nse_to_iso_date(raw) for raw in valid_dates_raw) if iso
        ]
        return {
            "success": False,
            "message": (
                f"Invalid expiry date '{expiry_date_iso}' for NSE:{symbol.upper()}. "
                "Use one of the dates in valid_dates."
            ),
            "valid_dates": valid_dates_iso,
        }

    url = (
        "https://www.nseindia.com/api/option-chain-v3"
        f"?type=Indices&symbol={symbol.upper()}&expiry={expiry_date_nse}"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
    }

    try:
        import requests

        session = requests.Session()
        session.get(
            "https://www.nseindia.com/option-chain", headers=headers, timeout=10
        )

        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        raw_data = response.json()

        filtered = raw_data.get("filtered", {})
        if not filtered or "data" not in filtered:
            return {
                "success": False,
                "message": (
                    f"No OI data found for NSE:{symbol.upper()} at expiry {expiry_date_iso}."
                ),
            }

        cleaned_rows: List[Dict[str, Any]] = []
        for row in filtered["data"]:
            ce = row.get("CE") or {}
            pe = row.get("PE") or {}
            cleaned_rows.append(
                {
                    "strike": _parse_float(row.get("strikePrice")),
                    "ce_oi": _parse_int(ce.get("openInterest")),
                    "ce_oi_chg": _parse_int(ce.get("changeinOpenInterest")),
                    "ce_vol": _parse_int(ce.get("totalTradedVolume")),
                    "ce_iv": _parse_float(ce.get("impliedVolatility")),
                    "ce_ltp": _parse_float(ce.get("lastPrice")),
                    "ce_chg": _parse_float(ce.get("change")),
                    "pe_oi": _parse_int(pe.get("openInterest")),
                    "pe_oi_chg": _parse_int(pe.get("changeinOpenInterest")),
                    "pe_vol": _parse_int(pe.get("totalTradedVolume")),
                    "pe_iv": _parse_float(pe.get("impliedVolatility")),
                    "pe_ltp": _parse_float(pe.get("lastPrice")),
                    "pe_chg": _parse_float(pe.get("change")),
                }
            )

        ce_tot = filtered.get("CE", {})
        pe_tot = filtered.get("PE", {})
        ce_oi = _parse_float(ce_tot.get("totOI")) or 0.0
        pe_oi = _parse_float(pe_tot.get("totOI")) or 0.0
        pcr = round(pe_oi / ce_oi, 4) if ce_oi > 0 else 0

        return {
            "success": True,
            "exchange": "NSE",
            "symbol": symbol.upper(),
            "expiry": expiry_date_iso,
            "display_expiry": expiry_date_nse,
            "underlying_price": _parse_float(
                raw_data.get("records", {}).get("underlyingValue")
            ),
            "timestamp": _nse_timestamp_to_iso(raw_data.get("records", {}).get("timestamp")),
            "pcr": pcr,
            "totals": {
                "ce_oi": _parse_int(ce_tot.get("totOI")),
                "pe_oi": _parse_int(pe_tot.get("totOI")),
                "ce_vol": _parse_int(ce_tot.get("totVol")),
                "pe_vol": _parse_int(pe_tot.get("totVol")),
            },
            "data": cleaned_rows,
            "message": f"Successfully retrieved OI data for NSE:{symbol.upper()}.",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to fetch NSE OI data: {str(e)}",
        }


def _fetch_bse_option_chain_oi_iso(symbol: str, expiry_date_iso: str) -> Dict[str, Any]:
    symbol = symbol.upper()
    scrip_code = BSE_SCRIP_CODES[symbol]

    expiry_result = fetch_bse_valid_expiry_dates(symbol)
    if not expiry_result.get("success"):
        return {
            "success": False,
            "message": expiry_result.get("error", "Failed to fetch BSE expiry dates."),
        }

    expiry_map = expiry_result.get("expiry_map", {})
    display_expiry = expiry_map.get(expiry_date_iso)
    if not display_expiry:
        return {
            "success": False,
            "message": (
                f"Invalid expiry date '{expiry_date_iso}' for BSE:{symbol}. "
                "Use one of the dates in valid_dates."
            ),
            "valid_dates": expiry_result.get("valid_dates", []),
        }

    url = "https://api.bseindia.com/BseIndiaAPI/api/DerivOptionChain_IV/w"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.bseindia.com",
        "Referer": "https://www.bseindia.com/",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        ),
    }

    try:
        import requests

        response = requests.get(
            url,
            params={
                "Expiry": display_expiry,
                "scrip_cd": scrip_code,
                "strprice": 0,
            },
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        raw_data = response.json()

        table = raw_data.get("Table", [])
        if not table:
            return {
                "success": False,
                "message": (
                    f"No OI data found for BSE:{symbol} at expiry {expiry_date_iso}."
                ),
            }

        cleaned_rows: List[Dict[str, Any]] = []
        for row in table:
            strike_value = row.get("Strike_Price1") or row.get("Strike_Price")
            cleaned_rows.append(
                {
                    "strike": _parse_float(strike_value),
                    "ce_oi": _parse_int(row.get("C_Open_Interest")),
                    "ce_oi_chg": _parse_int(row.get("C_Absolute_Change_OI")),
                    "ce_vol": _parse_int(row.get("C_Vol_Traded")),
                    "ce_iv": _parse_float(row.get("C_IV")),
                    "ce_ltp": _parse_float(row.get("C_Last_Trd_Price")),
                    "ce_chg": _parse_float(row.get("C_NetChange")),
                    "pe_oi": _parse_int(row.get("Open_Interest")),
                    "pe_oi_chg": _parse_int(row.get("Absolute_Change_OI")),
                    "pe_vol": _parse_int(row.get("Vol_Traded")),
                    "pe_iv": _parse_float(row.get("IV")),
                    "pe_ltp": _parse_float(row.get("Last_Trd_Price")),
                    "pe_chg": _parse_float(row.get("NetChange")),
                }
            )

        total_ce_oi = _parse_float(raw_data.get("tot_C_Open_Interest")) or 0.0
        total_pe_oi = _parse_float(raw_data.get("tot_Open_Interest")) or 0.0
        pcr = round(total_pe_oi / total_ce_oi, 4) if total_ce_oi > 0 else 0

        first_row = table[0] if table else {}

        return {
            "success": True,
            "exchange": "BSE",
            "symbol": symbol,
            "expiry": expiry_date_iso,
            "display_expiry": display_expiry,
            "underlying_price": _parse_float(first_row.get("UlaValue")),
            "timestamp": _bse_timestamp_to_iso(raw_data.get("ASON", {}).get("DT_TM")),
            "pcr": pcr,
            "totals": {
                "ce_oi": _parse_int(raw_data.get("tot_C_Open_Interest")),
                "pe_oi": _parse_int(raw_data.get("tot_Open_Interest")),
                "ce_vol": _parse_int(raw_data.get("tot_C_Vol_Traded")),
                "pe_vol": _parse_int(raw_data.get("tot_Vol_Traded")),
            },
            "data": cleaned_rows,
            "message": f"Successfully retrieved OI data for BSE:{symbol}.",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to fetch BSE OI data: {str(e)}",
        }


def fetch_option_chain_oi(exchange: str, symbol: str, expiry_date: str) -> Dict[str, Any]:
    exchange = exchange.upper().strip()
    symbol = validate_oi_symbol(exchange, symbol)
    expiry_date_iso = _parse_iso_date(expiry_date)

    if exchange == "NSE":
        return _fetch_nse_option_chain_oi_iso(symbol=symbol, expiry_date_iso=expiry_date_iso)
    if exchange == "BSE":
        return _fetch_bse_option_chain_oi_iso(symbol=symbol, expiry_date_iso=expiry_date_iso)

    raise ValidationError(
        f"Exchange '{exchange}' is not supported for OI data. Supported exchanges: NSE, BSE"
    )


def fetch_nse_option_chain_oi(symbol: str, expiry_date: str) -> Dict[str, Any]:
    """
    Legacy compatibility wrapper for NSE-only OI flow.
    Expects NSE expiry format DD-MMM-YYYY and forwards to the unified ISO flow.
    """
    symbol = validate_oi_symbol("NSE", symbol)
    validation_result = validate_nse_expiry_date(symbol, expiry_date)
    if not validation_result.get("valid"):
        return {
            "success": False,
            "message": f"Invalid expiry date '{expiry_date}' for {symbol}. Use one of the dates in valid_dates.",
            "valid_dates": validation_result.get("valid_dates", []),
        }

    expiry_date_iso = _nse_to_iso_date(expiry_date)
    if not expiry_date_iso:
        return {
            "success": False,
            "message": f"Invalid expiry date format '{expiry_date}'. Use DD-MMM-YYYY.",
        }

    result = _fetch_nse_option_chain_oi_iso(symbol=symbol, expiry_date_iso=expiry_date_iso)
    if result.get("success"):
        result["expiry"] = expiry_date
    return result


def process_option_chain_with_analysis(
    symbol: str,
    exchange: str,
    expiry_date: Optional[str] = "nearest",
    no_of_ITM: int = 5,
    no_of_OTM: int = 5,
) -> Dict[str, Any]:
    exchange = validate_exchange(exchange)
    symbol = validate_symbol(symbol)

    spot_price = get_current_spot_price(symbol, exchange)
    # Do not create a separate Options scraper instance here as it was unused.
    # We'll instantiate and use the scraper (opt_scraper) below when making the request.
    target_expiry = None
    if expiry_date and expiry_date.isdigit():
        target_expiry = int(expiry_date)

    from tv_scraper.scrapers.market_data.options import (
        DEFAULT_OPTION_COLUMNS,
        OPTIONS_SCANNER_URL,
    )

    payload = {
        "columns": DEFAULT_OPTION_COLUMNS,
        "filter": [
            {"left": "type", "operation": "equal", "right": "option"},
            {"left": "root", "operation": "equal", "right": symbol},
        ],
        "index_filters": [
            {"name": "underlying_symbol", "values": [f"{exchange}:{symbol}"]}
        ],
    }

    # Use the base scraper from Options to make the request
    opt_scraper = Options()
    resp = opt_scraper._make_request(
        OPTIONS_SCANNER_URL, method="POST", json_data=payload
    )
    data = resp.json()

    fields = data.get("fields", [])
    raw_symbols = data.get("symbols", [])

    expiry_groups: Dict[int, List[Dict[str, Any]]] = {}
    for item in raw_symbols:
        opt_data = {"symbol": item.get("s")}
        values = item.get("f", [])
        for i, field in enumerate(fields):
            opt_data[field] = values[i] if i < len(values) else None

        exp = opt_data.get("expiration")
        if exp:
            if exp not in expiry_groups:
                expiry_groups[exp] = []
            expiry_groups[exp].append(opt_data)

    available_expiries = sorted(expiry_groups.keys())
    if not available_expiries:
        return {"success": False, "message": "No expiries found"}

    current_date = int(datetime.now().strftime("%Y%m%d"))

    if expiry_date == "nearest":
        target_expiry = next(
            (e for e in available_expiries if e >= current_date), available_expiries[0]
        )
    elif expiry_date == "all":
        target_expiry = None  # handle below
    elif expiry_date and str(expiry_date).isdigit():
        target_expiry = int(expiry_date)
    else:
        target_expiry = available_expiries[0]

    def analyze_expiry(exp_val):
        opts = expiry_groups.get(exp_val, [])
        # Group by strike
        strikes = {}
        for o in opts:
            s = o["strike"]
            if s not in strikes:
                strikes[s] = {
                    "strike": s,
                    "call": None,
                    "put": None,
                    "dist": abs(s - spot_price),
                }
            strikes[s][o["option-type"]] = o

        sorted_strikes = sorted(strikes.values(), key=lambda x: x["strike"])
        atm_idx = next(
            (i for i, s in enumerate(sorted_strikes) if s["strike"] >= spot_price), 0
        )

        itm = sorted_strikes[:atm_idx][-no_of_ITM:]
        otm = sorted_strikes[atm_idx:][:no_of_OTM]

        res = []
        for s in itm + otm:
            for t in ["call", "put"]:
                if s[t]:
                    o = s[t]
                    o["option"] = t
                    o["strike_price"] = s["strike"]
                    o["distance_from_spot"] = s["dist"]
                    res.append(o)
        return res

    if target_expiry:
        final_data = analyze_expiry(target_expiry)
    else:
        final_data = []
        for e in available_expiries:
            final_data.extend(analyze_expiry(e))

    return {
        "success": True,
        "spot_price": spot_price,
        "data": final_data,
        "available_expiries": available_expiries,
        "returned_count": len(final_data),
    }