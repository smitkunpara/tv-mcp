"""
Option chain fetching and analytics service.

Uses the native *tv_scraper* ``Options`` API when available, falling back
to direct ``requests`` calls.
"""

from datetime import datetime
from http.cookies import SimpleCookie
from typing import Any, Dict, List, Optional

import requests

from ..core.validators import (
    validate_exchange,
    validate_symbol,
    ValidationError,
)
from ..core.settings import settings

# ---------------------------------------------------------------------------
# Native tv_scraper Options API (optional)
# ---------------------------------------------------------------------------

try:
    from tv_scraper.scrapers.market_data import Options as _NativeOptions

    _HAS_NATIVE_OPTIONS = True
except ImportError:
    _NativeOptions = None  # type: ignore[assignment,misc]
    _HAS_NATIVE_OPTIONS = False

_OPTION_COLUMNS: List[str] = [
    "ask",
    "bid",
    "currency",
    "delta",
    "expiration",
    "gamma",
    "iv",
    "option-type",
    "pricescale",
    "rho",
    "root",
    "strike",
    "theoPrice",
    "theta",
    "vega",
    "bid_iv",
    "ask_iv",
]


def fetch_option_chain_data(
    symbol: str,
    exchange: str,
    expiry_date: Optional[int] = None,
) -> Dict[str, Any]:
    cookies_str = settings.TRADINGVIEW_COOKIE
    cookies: Any = {}
    if cookies_str:
        try:
            cookie = SimpleCookie()
            cookie.load(cookies_str)
            cookies = {key: morsel.value for key, morsel in cookie.items()}
        except Exception:
            # Fallback to passing as string if parsing fails
            cookies = cookies_str

    try:
        # Request option chain data - matching browser format
        url = "https://scanner.tradingview.com/options/scan2?label-product=symbols-options"

        # Build filter - include expiry only if provided
        filter_conditions: list[dict[str, Any]] = [
            {"left": "type", "operation": "equal", "right": "option"},
            {"left": "root", "operation": "equal", "right": symbol},
        ]

        if expiry_date is not None:
            filter_conditions.append(
                {"left": "expiration", "operation": "equal", "right": expiry_date}
            )

        payload = {
            "columns": [
                "ask",
                "bid",
                "currency",
                "delta",
                "expiration",
                "gamma",
                "iv",
                "option-type",
                "pricescale",
                "rho",
                "root",
                "strike",
                "theoPrice",
                "theta",
                "vega",
                "bid_iv",
                "ask_iv",
            ],
            "filter": filter_conditions,
            "ignore_unknown_fields": False,
            "index_filters": [
                {"name": "underlying_symbol", "values": [f"{exchange}:{symbol}"]}
            ],
        }

        headers = {
            "Content-Type": "text/plain;charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Referer": "https://in.tradingview.com/",
            "Origin": "https://in.tradingview.com",
            "Connection": "keep-alive",
        }

        response = requests.post(
            url, json=payload, headers=headers, cookies=cookies, timeout=30
        )
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid JSON response: {str(e)}. Response content: {response.text[:200]}...",
                "data": None,
            }

        if not isinstance(data, dict):
            return {
                "success": False,
                "message": f"Expected dict response, got {type(data)}. Content: {str(data)[:200]}...",
                "data": None,
            }

        return {
            "success": True,
            "data": data,
            "total_count": data.get("totalCount", 0),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to fetch option chain: {str(e)}",
            "data": None,
        }


def get_current_spot_price(symbol: str, exchange: str) -> Dict[str, Any]:
    """Get current spot price of underlying symbol.

    Args:
        symbol: Symbol name (e.g., 'NIFTY')
        exchange: Exchange name (e.g., 'NSE')

    Returns:
        Dictionary with spot price and pricescale
    """
    cookies_str = settings.TRADINGVIEW_COOKIE
    cookies: Any = {}
    if cookies_str:
        try:
            cookie = SimpleCookie()
            cookie.load(cookies_str)
            cookies = {key: morsel.value for key, morsel in cookie.items()}
        except Exception:
            # Fallback to passing as string if parsing fails
            cookies = cookies_str

    try:
        url = "https://scanner.tradingview.com/global/scan2?label-product=options-overlay"

        payload = {
            "columns": ["close", "pricescale"],
            "ignore_unknown_fields": False,
            "symbols": {"tickers": [f"{exchange}:{symbol}"]},
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        response = requests.post(
            url, json=payload, headers=headers, cookies=cookies, timeout=30
        )
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid JSON response: {str(e)}. Response content: {response.text[:200]}...",
            }

        if (
            isinstance(data, dict)
            and data.get("symbols")
            and len(data["symbols"]) > 0
        ):
            symbol_data = data["symbols"][0]
            close_price = symbol_data["f"][0]
            pricescale = symbol_data["f"][1]

            return {
                "success": True,
                "spot_price": close_price,
                "pricescale": pricescale,
            }

        return {
            "success": False,
            "message": (
                f"No price data found. Response type: {type(data)}, "
                f'content: {str(data)[:200] if not isinstance(data, dict) else "dict without symbols"}'
            ),
        }

    except Exception as e:
        return {"success": False, "message": f"Failed to fetch spot price: {str(e)}"}


# ---------------------------------------------------------------------------
# Native wrappers
# ---------------------------------------------------------------------------


def _native_row_to_symbol_entry(
    row: Dict[str, Any],
    exchange: str,
    symbol: str,
) -> Dict[str, Any]:
    """Convert a native API data row to the legacy ``{s, f}`` format."""
    opt_type = row.get("option-type", "")
    exp = row.get("expiration", "")
    strike = row.get("strike", "")
    type_char = "C" if opt_type == "call" else "P"
    sym_name = f"{exchange}:{symbol}{exp}{type_char}{strike}"
    values: List[Any] = [row.get(col) for col in _OPTION_COLUMNS]
    return {"s": sym_name, "f": values}


def _fetch_chain_native(
    symbol: str,
    exchange: str,
    expiry_date: Optional[int] = None,
) -> Dict[str, Any]:
    """Fetch option chain via the native *tv_scraper* ``Options`` API.

    Returns data in the same envelope as :func:`fetch_option_chain_data` so
    that downstream processing code works unchanged.

    Falls back to ``{"success": False, ...}`` when the native library is
    unavailable or the API call fails.
    """
    if not _HAS_NATIVE_OPTIONS:
        return {
            "success": False,
            "message": "Native Options API not available",
            "data": None,
        }

    try:
        scraper = _NativeOptions()  # type: ignore[misc]
        kwargs: Dict[str, Any] = {
            "exchange": exchange,
            "symbol": symbol,
            "root": symbol,
        }
        if expiry_date is not None:
            kwargs["expiration"] = expiry_date

        result: Dict[str, Any] = scraper.get_chain_by_expiry(**kwargs)

        if result.get("status") != "success" or result.get("error") is not None:
            return {
                "success": False,
                "message": f"Native API error: {result.get('error', 'unknown')}",
                "data": None,
            }

        native_data: List[Dict[str, Any]] = result.get("data", [])

        symbols_list = [
            _native_row_to_symbol_entry(item, exchange, symbol)
            for item in native_data
        ]

        return {
            "success": True,
            "data": {
                "fields": list(_OPTION_COLUMNS),
                "symbols": symbols_list,
            },
            "total_count": len(symbols_list),
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Native fetch failed: {e}",
            "data": None,
        }


def _fetch_spot_price_native(symbol: str, exchange: str) -> Dict[str, Any]:
    """Fetch spot price — delegates to :func:`get_current_spot_price`.

    No native *tv_scraper* equivalent exists for spot price retrieval, so
    this thin wrapper simply calls the requests-based implementation.
    """
    return get_current_spot_price(symbol, exchange)


def process_option_chain_with_analysis(
    symbol: str,
    exchange: str,
    expiry_date: Optional[str] = "nearest",
    no_of_ITM: int = 5,
    no_of_OTM: int = 5,
) -> Dict[str, Any]:
    exchange = validate_exchange(exchange)
    symbol = validate_symbol(symbol)

    try:
        no_of_ITM = int(no_of_ITM)
    except (ValueError, TypeError):
        raise ValidationError(f"no_of_ITM must be a valid integer. Got: {no_of_ITM}")

    if no_of_ITM <= 0 or no_of_ITM > 20:
        raise ValidationError(
            f"no_of_ITM must be between 1 and 20. Got: {no_of_ITM}"
        )

    try:
        no_of_OTM = int(no_of_OTM)
    except (ValueError, TypeError):
        raise ValidationError(f"no_of_OTM must be a valid integer. Got: {no_of_OTM}")

    if no_of_OTM <= 0 or no_of_OTM > 20:
        raise ValidationError(
            f"no_of_OTM must be between 1 and 20. Got: {no_of_OTM}"
        )

    try:
        # Get current spot price
        spot_result = get_current_spot_price(symbol, exchange)
        if not spot_result["success"]:
            return {
                "success": False,
                "message": f"Failed to fetch spot price: {spot_result.get('message', 'Unknown error')}",
            }

        spot_price = spot_result["spot_price"]

        # Try native API first, fall back to legacy requests-based fetch
        option_result = _fetch_chain_native(symbol, exchange, expiry_date=None)
        if not option_result["success"]:
            option_result = fetch_option_chain_data(symbol, exchange, expiry_date=None)
        if not option_result["success"]:
            return {
                "success": False,
                "message": f"Failed to fetch option chain: {option_result.get('message', 'Unknown error')}",
            }

        raw_data = option_result["data"]
        fields = raw_data.get("fields", [])
        symbols_data = raw_data.get("symbols", [])

        if not symbols_data:
            return {
                "success": False,
                "message": "No option data available for the specified parameters",
            }

        # Group options by expiry and strike
        expiry_groups: Dict[Any, Dict] = {}

        for item in symbols_data:
            symbol_name = item["s"]
            values = item["f"]

            # Map fields to values
            option_data: Dict[str, Any] = {}
            for i, field in enumerate(fields):
                option_data[field] = values[i] if i < len(values) else None

            strike = option_data.get("strike")
            option_type = option_data.get("option-type")  # 'call' or 'put'
            expiration = option_data.get("expiration")

            if strike is None or option_type is None or expiration is None:
                continue

            # Initialize expiry group
            if expiration not in expiry_groups:
                expiry_groups[expiration] = {}

            # Initialize strike entry
            if strike not in expiry_groups[expiration]:
                expiry_groups[expiration][strike] = {
                    "strike": strike,
                    "call": None,
                    "put": None,
                    "distance_from_spot": abs(strike - spot_price),
                }

            # Calculate intrinsic and time value
            if option_type == "call":
                intrinsic = max(0, spot_price - strike)
            else:  # put
                intrinsic = max(0, strike - spot_price)

            theo_price: float = float(
                option_data.get("theoPrice") or 0
            )
            time_value = theo_price - intrinsic

            # Build option info
            option_info = {
                "symbol": symbol_name,
                "expiration": expiration,
                "ask": option_data.get("ask"),
                "bid": option_data.get("bid"),
                "delta": option_data.get("delta"),
                "gamma": option_data.get("gamma"),
                "theta": option_data.get("theta"),
                "vega": option_data.get("vega"),
                "rho": option_data.get("rho"),
                "iv": option_data.get("iv"),
                "bid_iv": option_data.get("bid_iv"),
                "ask_iv": option_data.get("ask_iv"),
                "theo_price": theo_price,
                "intrinsic_value": round(intrinsic, 2),
                "time_value": round(time_value, 2),
            }

            expiry_groups[expiration][strike][option_type] = option_info

        # Process each expiry and create flat array
        flat_options: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for expiration, strikes_dict in expiry_groups.items():
            # Sort all strikes
            all_strikes_by_price = sorted(
                strikes_dict.values(), key=lambda x: x["strike"]
            )

            # Find ATM index
            atm_index = 0
            for i, strike_data in enumerate(all_strikes_by_price):
                if strike_data["strike"] >= spot_price:
                    atm_index = i
                    break

            # Get ITM (below spot) and OTM (above spot) strikes
            available_itm = len(all_strikes_by_price[:atm_index])
            available_otm = len(all_strikes_by_price[atm_index:])

            # Determine actual number to return
            actual_itm = min(no_of_ITM, available_itm)
            actual_otm = min(no_of_OTM, available_otm)

            itm_strikes = (
                all_strikes_by_price[:atm_index][-actual_itm:]
                if actual_itm > 0
                else []
            )
            otm_strikes = all_strikes_by_price[atm_index:][:actual_otm]

            # Add warnings if insufficient data
            if available_itm < no_of_ITM:
                warnings.append(
                    f"Expiry {expiration}: Requested {no_of_ITM} ITM strikes but only {available_itm} available"
                )

            if available_otm < no_of_OTM:
                warnings.append(
                    f"Expiry {expiration}: Requested {no_of_OTM} OTM strikes but only {available_otm} available"
                )

            # Create flat array for this expiry
            for strike_data in itm_strikes + otm_strikes:
                strike = strike_data["strike"]
                distance_from_spot = strike_data["distance_from_spot"]

                # Add call option if exists
                if strike_data.get("call"):
                    call_option = strike_data["call"].copy()
                    call_option.update(
                        {
                            "option": "call",
                            "strike_price": strike,
                            "distance_from_spot": distance_from_spot,
                        }
                    )
                    flat_options.append(call_option)

                # Add put option if exists
                if strike_data.get("put"):
                    put_option = strike_data["put"].copy()
                    put_option.update(
                        {
                            "option": "put",
                            "strike_price": strike,
                            "distance_from_spot": distance_from_spot,
                        }
                    )
                    flat_options.append(put_option)

        # Extract all available expiries from the grouped data keys
        current_date = int(datetime.now().strftime("%Y%m%d"))
        available_expiries = sorted(list(expiry_groups.keys()))

        # Filter options based on expiry_date parameter
        if expiry_date is not None:
            if isinstance(expiry_date, str) and expiry_date.lower() == "nearest":
                # Find nearest future expiry
                nearest_expiry = None
                for exp in available_expiries:
                    if exp >= current_date:
                        nearest_expiry = exp
                        break
                if nearest_expiry is None and available_expiries:
                    # If no future expiry, take the most recent past one
                    nearest_expiry = available_expiries[-1]

                # Filter for nearest expiry using expiration field
                if nearest_expiry is not None:
                    flat_options = [
                        opt
                        for opt in flat_options
                        if opt.get("expiration") == nearest_expiry
                    ]
                else:
                    return {
                        "success": False,
                        "message": "No expiry dates found in option chain data",
                        "available_expiries": available_expiries,
                    }
            elif isinstance(expiry_date, str) and expiry_date.lower() == "all":
                # No filter, keep all
                pass
            else:
                # Specific expiry
                try:
                    target_expiry = (
                        int(expiry_date)
                        if isinstance(expiry_date, str)
                        else expiry_date
                    )

                    # Check if requested expiry exists
                    if target_expiry not in available_expiries:
                        return {
                            "success": False,
                            "message": f"Expiry date {target_expiry} not found in available data",
                            "available_expiries": available_expiries,
                        }

                    flat_options = [
                        opt
                        for opt in flat_options
                        if opt.get("expiration") == target_expiry
                    ]
                except ValueError:
                    return {
                        "success": False,
                        "message": f'Invalid expiry_date format: {expiry_date}. Use integer (YYYYMMDD), "nearest", or "all"',
                        "available_expiries": available_expiries,
                    }

        # Calculate analytics for the latest expiry (or all data if no specific expiry)
        analytics: Dict[str, Any] = {}
        latest_expiry = None
        if flat_options:
            # Find the latest expiry from the data
            expiries = set()
            for opt in flat_options:
                sym = opt.get("symbol", "")
                if "C" in sym:
                    expiry_part = sym.split("C")[0][-8:]
                elif "P" in sym:
                    expiry_part = sym.split("P")[0][-8:]
                else:
                    continue
                try:
                    exp_date = int(expiry_part)
                    expiries.add(exp_date)
                except ValueError:
                    continue

            latest_expiry = max(expiries) if expiries else None

            # Calculate analytics for latest expiry
            latest_expiry_options = [
                opt
                for opt in flat_options
                if str(latest_expiry) in opt.get("symbol", "")
            ]

            total_call_delta = sum(
                opt.get("delta", 0)
                for opt in latest_expiry_options
                if opt.get("option") == "call"
            )
            total_put_delta = sum(
                opt.get("delta", 0)
                for opt in latest_expiry_options
                if opt.get("option") == "put"
            )

            # Find ATM strike (closest to spot price)
            if latest_expiry_options:
                atm_strike = min(
                    (opt["strike_price"] for opt in latest_expiry_options),
                    key=lambda x: abs(x - spot_price),
                )
            else:
                atm_strike = spot_price

            analytics = {
                "atm_strike": atm_strike,
                "total_call_delta": round(total_call_delta, 4),
                "total_put_delta": round(total_put_delta, 4),
                "net_delta": round(total_call_delta + total_put_delta, 4),
                "total_strikes": (
                    len(
                        set(
                            opt["strike_price"] for opt in latest_expiry_options
                        )
                    )
                    if latest_expiry_options
                    else 0
                ),
            }

        # Build final result
        result: Dict[str, Any] = {
            "success": True,
            "spot_price": spot_price,
            "latest_expiry": latest_expiry,
            "analytics": analytics,
            "data": flat_options,
            "available_expiries": available_expiries,
            "requested_ITM": no_of_ITM,
            "requested_OTM": no_of_OTM,
            "returned_count": len(flat_options),
        }

        # Add warnings if any
        if warnings:
            result["warnings"] = warnings

        return result

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to process option chain: {str(e)}",
            "data": [],
        }
