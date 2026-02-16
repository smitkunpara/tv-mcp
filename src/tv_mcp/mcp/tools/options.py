"""
MCP tool handler for option chain with Greeks.
"""

from typing import Annotated, Optional, Union

from pydantic import Field

from src.tv_mcp.core.validators import VALID_EXCHANGES, ValidationError
from src.tv_mcp.services.options import process_option_chain_with_analysis

from ..serializers import serialize_error, serialize_success


async def get_option_chain_greeks(
    symbol: Annotated[
        Optional[str],
        Field(
            description="Underlying trading symbol (e.g., 'NIFTY', 'AAPL'). REQUIRED.",
        ),
    ] = None,
    exchange: Annotated[
        Optional[str],
        Field(
            description=(
                "Stock exchange name where the underlying symbol is traded (e.g., 'NSE', 'NASDAQ'). REQUIRED."
            ),
        ),
    ] = None,
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
    """
    try:
        if not exchange:
            return serialize_error("Missing REQUIRED field: 'exchange'. Please specify the exchange (e.g., 'NSE').")
        if not symbol:
            return serialize_error("Missing REQUIRED field: 'symbol'. Please specify the ticker (e.g., 'NIFTY').")

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
