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
        str,
        Field(
            description="Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY'). Required.",
            min_length=1,
            max_length=20,
        ),
    ],
    exchange: Annotated[
        str,
        Field(
            description=(
                "Stock exchange name (e.g., 'NSE'). "
                f"Valid examples: {', '.join(VALID_EXCHANGES[:5])}..."
            ),
            min_length=2,
            max_length=30,
        ),
    ],
    expiry_date: Annotated[
        Optional[Union[int, str]],
        Field(
            description=(
                "Option expiry date:\n"
                "- 'nearest' (default): NEAREST expiry only\n"
                "- 'all': ALL expiries grouped by date\n"
                "- int YYYYMMDD (e.g., 20251202): SPECIFIC expiry\n"
            ),
        ),
    ] = "nearest",
    no_of_ITM: Annotated[
        Union[int, str],
        Field(
            description=(
                "Number of In-The-Money strikes. Default 5, max 20."
            ),
        ),
    ] = 5,
    no_of_OTM: Annotated[
        Union[int, str],
        Field(
            description=(
                "Number of Out-of-The-Money strikes. Default 5, max 20."
            ),
        ),
    ] = 5,
) -> str:
    """
    Fetch real-time TradingView option chain with full Greeks.

    Returns delta, gamma, theta, vega, rho, IV, bid/ask/theo prices,
    intrinsic/time values for CALL/PUT at key strikes.
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
