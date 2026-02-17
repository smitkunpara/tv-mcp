"""
MCP tool handlers for paper trading operations.

Eight tools: place_order, close_position, view_positions, show_capital,
set_alert, alert_manager, view_available_alerts, remove_alert.
"""

from typing import Annotated, Optional, Dict, Any

from pydantic import Field

from src.tv_mcp.core.validators import ValidationError
from src.tv_mcp.core.settings import settings
from src.tv_mcp.services.paper_trading import PaperTradingEngine

from ..serializers import serialize_error, serialize_success


def _engine() -> PaperTradingEngine:
    """Return the lazily-initialized singleton engine."""
    engine = PaperTradingEngine()
    engine.initialize()
    return engine


async def _inject_alerts_if_enabled(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inject cached alerts into the result if INJECT_ALERTS_IN_ALL_TOOLS is enabled.
    
    This allows the AI to see triggered alerts even when using other tools,
    preventing alert loss when the AI is busy with other tasks.
    
    Note: Does NOT clear the cache - only alert_manager should clear it.
    """
    if not settings.INJECT_ALERTS_IN_ALL_TOOLS:
        return result
    
    engine = _engine()
    cached_alerts = await engine.get_cached_alerts(clear_cache=False)
    
    if cached_alerts:
        result["triggered_alerts"] = cached_alerts
        result["alert_notice"] = (
            f"{len(cached_alerts)} alert(s) triggered while you were busy. "
            "These alerts are also available via alert_manager."
        )
    
    return result


async def place_order(
    symbol: Annotated[
        str,
        Field(
            description="Trading symbol (e.g., 'NIFTY', 'RELIANCE', 'BTCUSD'). REQUIRED.",
        ),
    ],
    exchange: Annotated[
        str,
        Field(
            description="Exchange (e.g., 'NSE', 'BSE', 'CRYPTO'). REQUIRED.",
        ),
    ],
    entry_price: Annotated[
        float,
        Field(
            description="Entry/limit price at which to buy or sell. REQUIRED.",
        ),
    ],
    stop_loss: Annotated[
        float,
        Field(
            description="Stop loss price. Must be below entry for BUY, above for SELL. REQUIRED.",
        ),
    ],
    target: Annotated[
        float,
        Field(
            description="Target/take-profit price. REQUIRED.",
        ),
    ],
    lot_size: Annotated[
        int,
        Field(
            description="Number of lots/quantity to trade. REQUIRED.",
        ),
    ],
    trailing_sl: Annotated[
        bool,
        Field(
            description=(
                "Enable trailing stop loss. Use when strong directional "
                "movement is expected. Default: false."
            ),
        ),
    ] = False,
) -> str:
    """
    Place a paper trading order with entry price, stop-loss, target, and lot size.

    The system automatically determines BUY/SELL based on entry vs target.
    A background screener starts immediately to monitor SL/target hits.
    Risk:Reward ratio is validated against the configured minimum.
    Call alert_manager after placing to receive SL/target notifications.
    """
    try:
        result = await _engine().place_order(
            symbol=symbol,
            exchange=exchange,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            lot_size=lot_size,
            trailing_sl=trailing_sl,
        )
        result = await _inject_alerts_if_enabled(result)
        return serialize_success(result)
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def close_position(
    order_id: Annotated[
        int,
        Field(
            description="Order ID of the open position to close. REQUIRED.",
        ),
    ],
) -> str:
    """
    Manually close an open position at the current market price.

    Use this when analysis, news, or other factors suggest exiting
    before SL or target is hit. The trade is recorded in the database.
    """
    try:
        result = await _engine().close_position(order_id=order_id)
        result = await _inject_alerts_if_enabled(result)
        return serialize_success(result)
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def view_positions(
    filter_type: Annotated[
        Optional[str],
        Field(
            description=(
                "Filter positions: 'open', 'closed', or 'all'. "
                "Cannot be used together with order_id."
            ),
        ),
    ] = None,
    order_id: Annotated[
        Optional[int],
        Field(
            description=(
                "View a specific position by order ID. "
                "Cannot be used together with filter_type."
            ),
        ),
    ] = None,
) -> str:
    """
    View paper trading positions filtered by status or order ID.

    Provide EITHER filter_type OR order_id, not both.
    Returns open positions (in-memory) and/or closed positions (from database).
    """
    try:
        result = await _engine().view_positions(
            filter_type=filter_type, order_id=order_id
        )
        result = await _inject_alerts_if_enabled(result)
        return serialize_success(result)
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def show_capital() -> str:
    """
    Show paper trading capital details: available funds, invested amount,
    realized PnL, PnL percentage, and number of open positions.
    """
    try:
        result = await _engine().show_capital()
        result = await _inject_alerts_if_enabled(result)
        return serialize_success(result)
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def set_alert(
    alert_type: Annotated[
        str,
        Field(
            description="Alert type: 'price' or 'time'. REQUIRED.",
        ),
    ],
    symbol: Annotated[
        Optional[str],
        Field(
            description="Symbol for price alert (e.g., 'NIFTY'). Required for price alerts.",
        ),
    ] = None,
    exchange: Annotated[
        Optional[str],
        Field(
            description="Exchange for price alert (e.g., 'NSE'). Required for price alerts.",
        ),
    ] = None,
    price: Annotated[
        Optional[float],
        Field(
            description="Target price level for price alert. Required for price alerts.",
        ),
    ] = None,
    direction: Annotated[
        Optional[str],
        Field(
            description="'above' or 'below' — trigger when price crosses this level. Default: 'above'.",
        ),
    ] = None,
    minutes: Annotated[
        Optional[int],
        Field(
            description="Minutes for time alert (one-shot timer). Required for time alerts.",
        ),
    ] = None,
) -> str:
    """
    Set a price alert or time alert.

    Price alerts monitor a symbol and trigger when the price crosses
    the specified level. Time alerts trigger after the specified minutes.
    Time alerts are one-shot — set a new one if you need another ping.
    After setting, call alert_manager to wait for the trigger.
    """
    try:
        result = await _engine().set_alert(
            alert_type=alert_type,
            symbol=symbol,
            exchange=exchange,
            price=price,
            direction=direction,
            minutes=minutes,
        )
        result = await _inject_alerts_if_enabled(result)
        return serialize_success(result)
    except ValidationError as e:
        return serialize_error(str(e))
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def alert_manager() -> str:
    """
    Wait for and return triggered alerts (SL/target hits, price alerts, time alerts).

    This tool BLOCKS until an alert triggers or 5 minutes elapse.
    After receiving a response, if there are still active monitors
    (open positions or pending alerts), you MUST call this tool again.
    Do NOT stop calling until the response says all monitors are completed.
    """
    try:
        result = await _engine().alert_manager()
        return serialize_success(result)
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def view_available_alerts() -> str:
    """
    View all active alerts: both manually created alerts (price/time)
    and auto-generated trade monitoring alerts (SL/target watchers).
    """
    try:
        result = await _engine().view_available_alerts()
        result = await _inject_alerts_if_enabled(result)
        return serialize_success(result)
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")


async def remove_alert(
    alert_id: Annotated[
        int,
        Field(
            description="ID of the alert to remove. REQUIRED.",
        ),
    ],
) -> str:
    """
    Remove a manually created alert by its ID.

    Trade auto-alerts (SL/target monitors) cannot be removed — close the position instead.
    """
    try:
        result = await _engine().remove_alert(alert_id=alert_id)
        result = await _inject_alerts_if_enabled(result)
        return serialize_success(result)
    except Exception as e:
        return serialize_error(f"Unexpected error: {str(e)}")
