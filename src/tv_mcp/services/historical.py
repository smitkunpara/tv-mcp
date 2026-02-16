"""
Historical data service using tv_scraper.
"""

from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from tv_scraper import Streamer
from ..core.validators import (
    validate_exchange,
    validate_symbol,
    validate_timeframe,
    validate_indicators,
    ValidationError,
)
from ..core.auth import get_valid_jwt_token
from ..core.settings import settings
from ..transforms.ohlc import merge_ohlc_with_indicators


def fetch_historical_data(
    exchange: str,
    symbol: str,
    timeframe: str,
    numb_price_candles: int,
    indicators: List[str],
) -> Dict[str, Any]:
    exchange = validate_exchange(exchange)
    symbol = validate_symbol(symbol)
    timeframe = validate_timeframe(timeframe)

    try:
        numb_price_candles = int(numb_price_candles)
    except (ValueError, TypeError):
        raise ValidationError("Number of candles must be a valid integer.")

    if not (1 <= numb_price_candles <= 5000):
        raise ValidationError("Number of candles must be between 1 and 5000.")

    indicator_ids, indicator_versions, errors, warnings = validate_indicators(indicators)
    
    if errors:
        return {"success": False, "errors": errors, "message": f"Validation failed: {'; '.join(errors)}"}

    try:
        # Case 1: No indicators
        if not indicator_ids:
            streamer = Streamer(export_result=False)
            result = streamer.get_candles(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                numb_candles=numb_price_candles,
            )
            
            if result.get("status") == "failed":
                return {"success": False, "errors": [result.get("error", "Streamer failure")], "message": result.get("error")}
            
            data = result.get("data", {})
            merged_data = merge_ohlc_with_indicators({
                "ohlc": data.get("ohlcv", []),
                "indicator": data.get("indicators", {})
            })
            return {"success": True, "data": merged_data, "metadata": {"count": len(merged_data)}}

        # Case 2: With indicators (requires JWT token and batching)
        if not settings.TRADINGVIEW_COOKIE:
            raise ValidationError("TRADINGVIEW_COOKIE required for indicators.")

        # Batch indicators (free account limit)
        BATCH_SIZE = 2
        indicator_tuples = list(zip(indicator_ids, indicator_versions))
        batches = [indicator_tuples[i : i + BATCH_SIZE] for i in range(0, len(indicator_tuples), BATCH_SIZE)]

        combined_response: Dict[str, Any] = {"ohlcv": [], "indicators": {}}
        
        def fetch_batch(idx: int, batch: List[Tuple[str, str]]):
            token = get_valid_jwt_token()
            streamer = Streamer(export_result=False, websocket_jwt_token=token)
            return streamer.get_candles(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                numb_candles=numb_price_candles + idx,
                indicators=batch,
            )

        with ThreadPoolExecutor(max_workers=len(batches)) as executor:
            futures = {executor.submit(fetch_batch, i, b): i for i, b in enumerate(batches)}
            results = {}
            for future in as_completed(futures):
                idx = futures[future]
                res = future.result()
                if res.get("status") == "success":
                    results[idx] = res.get("data", {})

        for idx in sorted(results.keys()):
            data = results[idx]
            if not combined_response["ohlcv"]:
                combined_response["ohlcv"] = data.get("ohlcv", [])
            combined_response["indicators"].update(data.get("indicators", {}))

        merged_data = merge_ohlc_with_indicators({
            "ohlc": combined_response["ohlcv"],
            "indicator": combined_response["indicators"]
        })

        return {
            "success": True,
            "data": merged_data,
            "metadata": {
                "exchange": exchange,
                "symbol": symbol,
                "timeframe": timeframe,
                "count": len(merged_data),
                "batches": len(batches),
            }
        }

    except Exception as e:
        return {"success": False, "errors": [f"TradingView API error: {str(e)}"], "message": str(e)}
