"""
Options service using tv_scraper.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from tv_scraper import Options, Overview
from tv_mcp.core.validators import validate_exchange, validate_symbol, ValidationError


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
            "error": f"Symbol '{symbol}' not supported for NSE OI data. Supported: {', '.join(supported)}"
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
        session.get("https://www.nseindia.com/option-chain", headers=headers, timeout=10)
        
        response = session.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        expiry_dates = data.get("expiryDates", [])
        if not expiry_dates:
            return {
                "success": False,
                "error": f"No expiry dates found for {symbol}"
            }
        
        return {
            "success": True,
            "expiryDates": expiry_dates
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch valid expiry dates from NSE: {str(e)}"
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
        return {
            "success": False,
            "valid": False,
            "error": result.get("error")
        }
    
    valid_dates = result.get("expiryDates", [])
    
    # Check if provided date is in the list
    if expiry_date in valid_dates:
        return {
            "success": True,
            "valid": True,
            "date": expiry_date
        }
    
    # Date is invalid - return helpful error
    return {
        "success": False,
        "valid": False,
        "provided_date": expiry_date,
        "valid_dates": valid_dates,
        "error": f"Invalid expiry date '{expiry_date}' for {symbol}. Please use one of the available expiry dates."
    }


def get_current_spot_price(symbol: str, exchange: str) -> float:
    scraper = Overview(export_result=False)
    result = scraper.get_overview(exchange=exchange, symbol=symbol, fields=["close"])
    if result.get("status") == "success":
        price = (result.get("data") or {}).get("close")
        if price is not None:
            return float(price)
    raise Exception(f"Failed to fetch spot price for {symbol}: {result.get('error', 'price unavailable or None')}")


def fetch_nse_option_chain_oi(
    symbol: str,
    expiry_date: str
) -> Dict[str, Any]:
    """
    Fetch and clean NSE Option Chain OI data.
    Supported symbols: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY, NIFTYNXT50.
    Expiry format: DD-MMM-YYYY (e.g., 19-Feb-2026).
    """
    # Validate symbol against supported NSE indices
    supported = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"]
    if symbol.upper() not in supported:
        raise ValidationError(f"Symbol '{symbol}' not supported for NSE OI data. Supported: {', '.join(supported)}")

    # Validate expiry date
    validation_result = validate_nse_expiry_date(symbol, expiry_date)
    if not validation_result.get("valid"):
        valid_dates = validation_result.get("valid_dates", [])
        return {
            "success": False,
            "message": f"Invalid expiry date '{expiry_date}' for {symbol}. Use one of the dates in valid_dates.",
            "valid_dates": valid_dates,
        }

    url = f"https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol={symbol.upper()}&expiry={expiry_date}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
    }

    try:
        import requests
        # Create session to handle cookies which NSE often requires
        session = requests.Session()
        # Hit main page first to get cookies
        session.get("https://www.nseindia.com/option-chain", headers=headers, timeout=10)
        
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        raw_data = response.json()

        filtered = raw_data.get("filtered", {})
        if not filtered or "data" not in filtered:
            return {"success": False, "message": f"No data found for {symbol} with expiry {expiry_date}."}

        cleaned_rows = []
        for row in filtered["data"]:
            ce = row.get("CE") or {}
            pe = row.get("PE") or {}
            cleaned_rows.append({
                "strike": row.get("strikePrice"),
                "ce_oi": ce.get("openInterest"),
                "ce_oi_chg": ce.get("changeinOpenInterest"),
                "ce_vol": ce.get("totalTradedVolume"),
                "ce_iv": ce.get("impliedVolatility"),
                "ce_ltp": ce.get("lastPrice"),
                "ce_chg": ce.get("change"),
                "pe_oi": pe.get("openInterest"),
                "pe_oi_chg": pe.get("changeinOpenInterest"),
                "pe_vol": pe.get("totalTradedVolume"),
                "pe_iv": pe.get("impliedVolatility"),
                "pe_ltp": pe.get("lastPrice"),
                "pe_chg": pe.get("change"),
            })

        # Totals and PCR
        ce_tot = filtered.get("CE", {})
        pe_tot = filtered.get("PE", {})
        ce_oi = ce_tot.get("totOI", 0)
        pe_oi = pe_tot.get("totOI", 0)
        pcr = round(pe_oi / ce_oi, 4) if ce_oi > 0 else 0

        return {
            "success": True,
            "symbol": symbol.upper(),
            "expiry": expiry_date,
            "underlying_price": raw_data.get("records", {}).get("underlyingValue"),
            "timestamp": raw_data.get("records", {}).get("timestamp"),
            "pcr": pcr,
            "totals": {
                "CE": ce_tot,
                "PE": pe_tot
            },
            "data": cleaned_rows,
            "message": f"Successfully retrieved NSE OI data for {symbol}. PCR is {pcr}. Analyze 'data' for strike-wise OI shifts."
        }

    except Exception as e:
        return {
            "success": False, 
            "message": f"Failed to fetch NSE OI data: {str(e)}. Ensure the expiry format is DD-MMM-YYYY (e.g., 19-Feb-2026)."
        }


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
    
    scraper = Options(export_result=False)
    # Using a large number or something that returns all
    # tv_scraper.Options.get_chain_by_expiry needs a specific expiry.
    # To get all, we might need to use a different approach or just fetch by nearest if that's what's requested.
    
    # Actually, let's just fetch all by searching for root.
    # The tv_scraper.Options class has get_chain_by_expiry which uses root.
    # If we want all expiries, we might need to use the scanner directly or call multiple times.
    # For now, let's assume we fetch for the specific expiry if provided, or nearest.
    
    # We'll use the native scanner approach if we want all, but tv_scraper provides a nice wrapper.
    # Let's see if we can get all expiries.
    
    # For simplicity in this refactor, I'll use the native scraper to get data for the nearest or specific expiry.
    
    target_expiry = None
    if expiry_date and expiry_date.isdigit():
        target_expiry = int(expiry_date)
    
    # If we don't have a target expiry, we need to find it.
    # This is where the old code was better at finding expiries.
    # I'll keep the grouping logic but fetch data using tv_scraper.
    
    # Wait, the tv_scraper.Options.get_chain_by_expiry uses expiration filter.
    # If we don't provide it, it fails.
    
    # I'll use the Screener to find expiries first, or just use the old request logic for that part
    # but the user wants "remove unwanted code".
    
    # Let's use tv_scraper.Options with a trick to get more data if possible.
    # Actually, I'll just use the old grouping logic but make it cleaner.
    
    # I will use tv_scraper's internal execute_request logic but exposed.
    # Since I don't want to rewrite the whole Options scraper, I'll use it as much as possible.
    
    from tv_scraper.scrapers.market_data.options import OPTIONS_SCANNER_URL, DEFAULT_OPTION_COLUMNS
    
    payload = {
        "columns": DEFAULT_OPTION_COLUMNS,
        "filter": [
            {"left": "type", "operation": "equal", "right": "option"},
            {"left": "root", "operation": "equal", "right": symbol},
        ],
        "index_filters": [{"name": "underlying_symbol", "values": [f"{exchange}:{symbol}"]}],
    }
    
    # Use the base scraper from Options to make the request
    opt_scraper = Options()
    resp = opt_scraper._make_request(OPTIONS_SCANNER_URL, method="POST", json_data=payload)
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
        target_expiry = next((e for e in available_expiries if e >= current_date), available_expiries[0])
    elif expiry_date == "all":
        target_expiry = None # handle below
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
                strikes[s] = {"strike": s, "call": None, "put": None, "dist": abs(s - spot_price)}
            strikes[s][o["option-type"]] = o
            
        sorted_strikes = sorted(strikes.values(), key=lambda x: x["strike"])
        atm_idx = next((i for i, s in enumerate(sorted_strikes) if s["strike"] >= spot_price), 0)
        
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
        "returned_count": len(final_data)
    }
