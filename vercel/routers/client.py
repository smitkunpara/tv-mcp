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
    validate_exchange,
    validate_symbol,
    validate_timeframe,
)
from src.tv_mcp.services.historical import fetch_historical_data
from src.tv_mcp.services.news import fetch_news_headlines, fetch_news_content
from src.tv_mcp.services.technicals import fetch_all_indicators
from src.tv_mcp.services.ideas import fetch_ideas
from src.tv_mcp.services.minds import fetch_minds
from src.tv_mcp.services.options import process_option_chain_with_analysis

from ..auth import verify_client
from ..schemas import (
    HistoricalDataRequest,
    NewsHeadlinesRequest,
    NewsContentRequest,
    AllIndicatorsRequest,
    IdeasRequest,
    MindsRequest,
    OptionChainGreeksRequest,
)

router = APIRouter()


# ── POST /historical-data ──────────────────────────────────────────


@router.post("/historical-data", dependencies=[Depends(verify_client)])
async def get_historical_data_endpoint(request: HistoricalDataRequest) -> dict:
    try:
        # Coerce numb_price_candles
        try:
            numb_price_candles = (
                int(request.numb_price_candles)
                if isinstance(request.numb_price_candles, str)
                else request.numb_price_candles
            )
            if not (1 <= numb_price_candles <= 5000):
                raise ValidationError(
                    f"numb_price_candles must be between 1 and 5000, got {numb_price_candles}"
                )
        except ValueError:
            raise ValidationError("numb_price_candles must be a valid integer")

        result = fetch_historical_data(
            exchange=request.exchange,
            symbol=request.symbol,
            timeframe=request.timeframe,
            numb_price_candles=numb_price_candles,
            indicators=request.indicators,
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /news-headlines ───────────────────────────────────────────


@router.post("/news-headlines", dependencies=[Depends(verify_client)])
async def get_news_headlines_endpoint(request: NewsHeadlinesRequest) -> dict:
    try:
        headlines = fetch_news_headlines(
            symbol=request.symbol,
            exchange=request.exchange,
            provider=request.provider,
            area=request.area,
        )

        if not headlines:
            return {"data": "headlines[0]:"}

        return {"data": toon_encode({"headlines": headlines})}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch news: {str(e)}")


# ── POST /news-content ─────────────────────────────────────────────


@router.post("/news-content", dependencies=[Depends(verify_client)])
async def get_news_content_endpoint(request: NewsContentRequest) -> dict:
    try:
        articles = fetch_news_content(request.story_paths)
        return {"data": toon_encode({"articles": articles})}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch news content: {str(e)}")


# ── POST /all-indicators ───────────────────────────────────────────


@router.post("/all-indicators", dependencies=[Depends(verify_client)])
async def get_all_indicators_endpoint(request: AllIndicatorsRequest) -> dict:
    try:
        exchange = validate_exchange(request.exchange)
        symbol = validate_symbol(request.symbol)
        timeframe = validate_timeframe(request.timeframe)

        result = fetch_all_indicators(exchange=exchange, symbol=symbol, timeframe=timeframe)
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /ideas ─────────────────────────────────────────────────────


@router.post("/ideas", dependencies=[Depends(verify_client)])
async def get_ideas_endpoint(request: IdeasRequest) -> dict:
    try:
        # Coerce startPage
        try:
            startPage = int(request.startPage) if isinstance(request.startPage, str) else request.startPage
            if not (1 <= startPage <= 10):
                raise ValidationError(f"startPage must be between 1 and 10, got {startPage}")
        except ValueError:
            raise ValidationError("startPage must be a valid integer")

        # Coerce endPage
        try:
            endPage = int(request.endPage) if isinstance(request.endPage, str) else request.endPage
            if not (1 <= endPage <= 10):
                raise ValidationError(f"endPage must be between 1 and 10, got {endPage}")
            if endPage < startPage:
                raise ValidationError(
                    f"endPage ({endPage}) must be greater than or equal to startPage ({startPage})"
                )
        except ValueError:
            raise ValidationError("endPage must be a valid integer")

        symbol = validate_symbol(request.symbol)

        result = fetch_ideas(
            symbol=symbol,
            exchange=getattr(request, 'exchange', 'BITSTAMP'),
            startPage=startPage,
            endPage=endPage,
            sort=request.sort,
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /minds ─────────────────────────────────────────────────────


@router.post("/minds", dependencies=[Depends(verify_client)])
async def get_minds_endpoint(request: MindsRequest) -> dict:
    try:
        limit = None
        if request.limit is not None:
            try:
                limit = int(request.limit) if isinstance(request.limit, str) else request.limit
                if limit <= 0:
                    raise ValidationError(f"limit must be a positive integer, got {limit}")
            except ValueError:
                raise ValidationError("limit must be a valid integer")

        symbol = validate_symbol(request.symbol)
        exchange = validate_exchange(request.exchange)

        result = fetch_minds(
            symbol=symbol,
            exchange=exchange,
            limit=limit,
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ── POST /option-chain-greeks ──────────────────────────────────────


@router.post("/option-chain-greeks", dependencies=[Depends(verify_client)])
async def get_option_chain_greeks_endpoint(request: OptionChainGreeksRequest) -> dict:
    try:
        # Coerce no_of_ITM
        try:
            no_of_ITM = int(request.no_of_ITM) if isinstance(request.no_of_ITM, str) else request.no_of_ITM
            if not (1 <= no_of_ITM <= 20):
                raise ValidationError(f"no_of_ITM must be between 1 and 20, got {no_of_ITM}")
        except ValueError:
            raise ValidationError("no_of_ITM must be a valid integer")

        # Coerce no_of_OTM
        try:
            no_of_OTM = int(request.no_of_OTM) if isinstance(request.no_of_OTM, str) else request.no_of_OTM
            if not (1 <= no_of_OTM <= 20):
                raise ValidationError(f"no_of_OTM must be between 1 and 20, got {no_of_OTM}")
        except ValueError:
            raise ValidationError("no_of_OTM must be a valid integer")

        exchange = validate_exchange(request.exchange)
        symbol = validate_symbol(request.symbol)

        # Coerce expiry_date to str | None for service signature
        expiry_date: str | None = str(request.expiry_date) if request.expiry_date is not None else None

        result = process_option_chain_with_analysis(
            symbol=symbol,
            exchange=exchange,
            expiry_date=expiry_date,
            no_of_ITM=no_of_ITM,
            no_of_OTM=no_of_OTM,
        )
        return {"data": toon_encode(result)}

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
