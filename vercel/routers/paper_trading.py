"""
Paper Trading REST endpoints.

Comment out the import and include_router in ``vercel/app.py``
to disable these endpoints entirely.
"""

from fastapi import APIRouter, Depends, HTTPException
from toon import encode as toon_encode

from src.tv_mcp.core.validators import ValidationError
from src.tv_mcp.services.paper_trading import PaperTradingEngine

from ..auth import verify_client
from ..schemas import (
    PlaceOrderRequest,
    ClosePositionRequest,
    ViewPositionsRequest,
    SetAlertRequest,
    RemoveAlertRequest,
    GenericDataResponse,
)

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])


def _engine() -> PaperTradingEngine:
    """Return the lazily-initialized singleton engine."""
    engine = PaperTradingEngine()
    engine.initialize()
    return engine


# ── POST /paper-trading/place-order ──────────────────────────────


@router.post(
    "/place-order",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def place_order_endpoint(request: PlaceOrderRequest) -> dict:
    try:
        result = await _engine().place_order(
            symbol=request.symbol,
            exchange=request.exchange,
            stop_loss=request.stop_loss,
            target=request.target,
            lot_size=request.lot_size,
            entry_price=request.entry_price,
            order_type=request.order_type,
            trailing_sl_step_pct=request.trailing_sl_step_pct,
        )
        return {"data": toon_encode(result)}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /paper-trading/close-position ───────────────────────────


@router.post(
    "/close-position",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def close_position_endpoint(request: ClosePositionRequest) -> dict:
    try:
        result = await _engine().close_position(order_id=request.order_id)
        return {"data": toon_encode(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /paper-trading/view-positions ───────────────────────────


@router.post(
    "/view-positions",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def view_positions_endpoint(request: ViewPositionsRequest) -> dict:
    try:
        result = await _engine().view_positions(
            filter_type=request.filter_type, order_id=request.order_id
        )
        return {"data": toon_encode(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── GET /paper-trading/show-capital ──────────────────────────────


@router.get(
    "/show-capital",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def show_capital_endpoint() -> dict:
    try:
        result = await _engine().show_capital()
        return {"data": toon_encode(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /paper-trading/set-alert ────────────────────────────────


@router.post(
    "/set-alert",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def set_alert_endpoint(request: SetAlertRequest) -> dict:
    try:
        result = await _engine().set_alert(
            alert_type=request.alert_type,
            symbol=request.symbol,
            exchange=request.exchange,
            price=request.price,
            minutes=request.minutes,
        )
        return {"data": toon_encode(result)}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── GET /paper-trading/alert-manager ─────────────────────────────


@router.get(
    "/alert-manager",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def alert_manager_endpoint() -> dict:
    try:
        result = await _engine().alert_manager()
        return {"data": toon_encode(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── GET /paper-trading/view-alerts ───────────────────────────────


@router.get(
    "/view-alerts",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def view_alerts_endpoint() -> dict:
    try:
        result = await _engine().view_available_alerts()
        return {"data": toon_encode(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /paper-trading/remove-alert ─────────────────────────────


@router.post(
    "/remove-alert",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def remove_alert_endpoint(request: RemoveAlertRequest) -> dict:
    try:
        result = await _engine().remove_alert(alert_id=request.alert_id)
        return {"data": toon_encode(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
