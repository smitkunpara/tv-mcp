"""
MCP tool handler for option chain with Greeks.
"""

from typing import Annotated, Optional, Union

from pydantic import Field

from src.tv_mcp.core.validators import ValidationError
from src.tv_mcp.services.options import (
    fetch_option_chain_oi,
    process_option_chain_with_analysis,
)

from ..serializers import serialize_error, serialize_success


async def get_option_chain_oi(
    exchange: Annotated[
        str,
        Field(
            description=(
                "Stock exchange for OI data. ONLY supports: NSE, BSE. REQUIRED."
            ),
        ),
    ],
    symbol: Annotated[
        str,
        Field(
            description=(
                "Index symbol for the selected exchange. "
                "For NSE: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY, NIFTYNXT50. "
                "For BSE: SENSEX, BANKEX, SX50. REQUIRED."
            ),
        ),
    ],
    expiry_date: Annotated[
        str,
        Field(
            description=(
                "Option expiry date in ISO format 'YYYY-MM-DD' (e.g., '2026-03-25'). "
                "REQUIRED. If invalid, error response includes valid_dates."
            ),
        ),
    ],
) -> str:
    """
    Fetch real-time Option Chain Open Interest (OI) and Put-Call Ratio (PCR) for Indian indices.
    Supports only NSE and BSE in this tool, with exchange-aware symbol validation.
    Returns strike-wise combined CE/PE OI details (not Greeks).
    """
    try:
        result = fetch_option_chain_oi(
            exchange=exchange,
            symbol=symbol,
            expiry_date=expiry_date,
        )
        if not result.get("success"):
            details = (
                {"valid_dates": result["valid_dates"]}
                if result.get("valid_dates")
                else None
            )
            return serialize_error(result.get("message", "Unknown error"), details=details)
        return serialize_success(result)
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def get_option_chain_greeks(
    symbol: Annotated[
        str,
        Field(
            description="Underlying trading symbol (e.g., 'NIFTY', 'AAPL'). REQUIRED.",
        ),
    ],
    exchange: Annotated[
        str,
        Field(
            description=(
                "Stock exchange name where the underlying symbol is traded (e.g., 'NSE', 'NASDAQ'). REQUIRED."
            ),
        ),
    ],
    expiry_date: Annotated[
        Optional[Union[int, str]],
        Field(
            description=(
                "Filter option chain by expiry date:\n"
                "- 'nearest' (default): Returns the closest future expiry\n"
                "- 'all': Returns all available expiries\n"
                "- YYYYMMDD (e.g., 20251202): Returns a specific expiry date\n"
            ),
        ),
    ] = "nearest",
    no_of_ITM: Annotated[
        Union[int, str],
        Field(
            description=(
                "Number of In-The-Money strikes to retrieve. Default 5, max 20."
            ),
        ),
    ] = 5,
    no_of_OTM: Annotated[
        Union[int, str],
        Field(
            description=(
                "Number of Out-of-The-Money strikes to retrieve. Default 5, max 20."
            ),
        ),
    ] = 5,
) -> str:
    """
    Fetch real-time Option Chain data with Greeks analysis (Delta, Gamma, Theta, Vega, Rho, IV).
    This tool uses TradingView data and can work with exchanges/symbols supported by TradingView.
    """
    try:
        parsed_itm = int(no_of_ITM) if isinstance(no_of_ITM, str) else no_of_ITM
        parsed_otm = int(no_of_OTM) if isinstance(no_of_OTM, str) else no_of_OTM
        expiry: Optional[str] = (
            str(expiry_date) if isinstance(expiry_date, int) else expiry_date
        )
        result = process_option_chain_with_analysis(
            symbol=symbol,
            exchange=exchange,
            expiry_date=expiry,
            no_of_ITM=parsed_itm,
            no_of_OTM=parsed_otm,
        )
        return serialize_success(result)
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")
