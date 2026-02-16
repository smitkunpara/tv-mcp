"""
Client-authenticated routes — all 7 business POST endpoints.

Each endpoint uses ``verify_client`` for auth, delegates to the matching
service function from ``src.tv_mcp.services``, and returns a TOON-encoded
response envelope.
"""

from fastapi import APIRouter, Depends, HTTPException
from toon import encode as toon_encode

from src.tv_mcp.core.validators import (
    ValidationError,
)
from src.tv_mcp.services.historical import fetch_historical_data
from src.tv_mcp.services.news import fetch_news_headlines, fetch_news_content
from src.tv_mcp.services.technicals import fetch_all_indicators
from src.tv_mcp.services.ideas import fetch_ideas
from src.tv_mcp.services.minds import fetch_minds
from src.tv_mcp.services.options import process_option_chain_with_analysis, fetch_nse_option_chain_oi

from ..auth import verify_client
from ..schemas import (
    HistoricalDataRequest,
    NewsHeadlinesRequest,
    NewsContentRequest,
    AllIndicatorsRequest,
    IdeasRequest,
    MindsRequest,
    OptionChainGreeksRequest,
    NseOptionChainOiRequest,
    GenericDataResponse,
)

router = APIRouter()


# ── POST /historical-data ──────────────────────────────────────────


@router.post(
    "/historical-data",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def get_historical_data_endpoint(request: HistoricalDataRequest) -> dict:
    try:
        result = fetch_historical_data(
            exchange=request.exchange,
            symbol=request.symbol,
            timeframe=request.timeframe,
            numb_price_candles=int(request.numb_price_candles),
            indicators=request.indicators,
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /news-headlines ───────────────────────────────────────────


@router.post(
    "/news-headlines",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def get_news_headlines_endpoint(request: NewsHeadlinesRequest) -> dict:
    try:
        headlines = fetch_news_headlines(
            symbol=request.symbol,
            exchange=request.exchange,
            provider=request.provider,
            area=request.area,
            start_datetime=request.start_datetime,
            end_datetime=request.end_datetime,
        )

        if not headlines:
            return {"data": "headlines[0]:"}

        return {"data": toon_encode({"headlines": headlines})}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch news: {str(e)}")


# ── POST /news-content ─────────────────────────────────────────────


@router.post(
    "/news-content",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def get_news_content_endpoint(request: NewsContentRequest) -> dict:
    try:
        articles = fetch_news_content(request.story_ids)
        return {"data": toon_encode({"articles": articles})}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch news content: {str(e)}")


# ── POST /all-indicators ───────────────────────────────────────────


@router.post(
    "/all-indicators",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def get_all_indicators_endpoint(request: AllIndicatorsRequest) -> dict:
    try:
        result = fetch_all_indicators(
            exchange=request.exchange, 
            symbol=request.symbol, 
            timeframe=request.timeframe
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /ideas ─────────────────────────────────────────────────────


@router.post("/ideas", dependencies=[Depends(verify_client)], response_model=GenericDataResponse)
async def get_ideas_endpoint(request: IdeasRequest) -> dict:
    try:
        result = fetch_ideas(
            symbol=request.symbol,
            exchange=request.exchange,
            startPage=int(request.startPage),
            endPage=int(request.endPage),
            sort=request.sort,
            start_datetime=request.start_datetime,
            end_datetime=request.end_datetime,
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /minds ─────────────────────────────────────────────────────


@router.post("/minds", dependencies=[Depends(verify_client)], response_model=GenericDataResponse)
async def get_minds_endpoint(request: MindsRequest) -> dict:
    try:
        result = fetch_minds(
            symbol=request.symbol,
            exchange=request.exchange,
            limit=int(request.limit),
            start_datetime=request.start_datetime,
            end_datetime=request.end_datetime,
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /option-chain-greeks ──────────────────────────────────────


@router.post(
    "/option-chain-greeks",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def get_option_chain_greeks_endpoint(request: OptionChainGreeksRequest) -> dict:
    try:
        # Coerce expiry_date to str | None for service signature
        expiry_date: str | None = str(request.expiry_date) if request.expiry_date is not None else None

        result = process_option_chain_with_analysis(
            symbol=request.symbol,
            exchange=request.exchange,
            expiry_date=expiry_date,
            no_of_ITM=int(request.no_of_ITM),
            no_of_OTM=int(request.no_of_OTM),
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /nse-option-chain-oi ─────────────────────────────────────


@router.post(
    "/nse-option-chain-oi",
    dependencies=[Depends(verify_client)],
    response_model=GenericDataResponse,
)
async def get_nse_option_chain_oi_endpoint(request: NseOptionChainOiRequest) -> dict:
    try:
        result = fetch_nse_option_chain_oi(
            symbol=request.symbol,
            expiry_date=request.expiry_date,
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
