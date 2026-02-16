"""
Options service using tv_scraper.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from tv_scraper import Options, Overview
from tv_mcp.core.validators import validate_exchange, validate_symbol, ValidationError


def get_current_spot_price(symbol: str, exchange: str) -> float:
    scraper = Overview(export_result=False)
    result = scraper.get_overview(exchange=exchange, symbol=symbol, fields=["close"])
    if result.get("status") == "success":
        return result.get("data", {}).get("close", 0.0)
    raise Exception(f"Failed to fetch spot price: {result.get('error')}")


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
