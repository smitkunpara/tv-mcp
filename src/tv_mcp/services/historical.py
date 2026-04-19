"""
Historical data service using tv_scraper.
"""

from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from tv_scraper import Streamer
from tv_mcp.core.validators import (
    INDICATOR_FIELD_MAPPING,
    validate_exchange,
    validate_symbol,
    validate_timeframe,
    validate_indicators,
    validate_candle_count,
    ValidationError,
)
from tv_mcp.core.settings import settings
from tv_mcp.transforms.ohlc import merge_ohlc_with_indicators
from tv_mcp.services._compat import build_scraper


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
    numb_price_candles = validate_candle_count(numb_price_candles)

    indicator_ids, indicator_versions, errors, _warnings = validate_indicators(indicators)
    
    if errors:
        return {"success": False, "errors": errors, "message": f"Validation failed: {'; '.join(errors)}"}

    try:
        # Case 1: No indicators
        if not indicator_ids:
            streamer = build_scraper(Streamer)
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

        # Case 2: With indicators (requires authenticated cookie and batching)
        if not settings.TRADINGVIEW_COOKIE:
            raise ValidationError("TRADINGVIEW_COOKIE required for indicators.")

        # Batch indicators (free account limit)
        BATCH_SIZE = 2
        MAX_BATCH_ATTEMPTS = 3
        indicator_tuples = list(zip(indicator_ids, indicator_versions))
        batches = [indicator_tuples[i : i + BATCH_SIZE] for i in range(0, len(indicator_tuples), BATCH_SIZE)]

        combined_response: Dict[str, Any] = {"ohlcv": [], "indicators": {}}
        
        def fetch_batch(idx: int, batch: List[Tuple[str, str]]):
            last_error = "Streamer failure"
            for _ in range(MAX_BATCH_ATTEMPTS):
                try:
                    streamer = build_scraper(Streamer, cookie=settings.TRADINGVIEW_COOKIE)
                    result = streamer.get_candles(
                        exchange=exchange,
                        symbol=symbol,
                        timeframe=timeframe,
                        numb_candles=numb_price_candles + idx,
                        indicators=batch,
                    )
                except Exception as exc:
                    last_error = str(exc) or last_error
                    continue

                if result.get("status") == "success":
                    return result

                last_error = result.get("error", last_error)

            return {"status": "failed", "error": last_error}

        with ThreadPoolExecutor(max_workers=len(batches)) as executor:
            futures = {executor.submit(fetch_batch, i, b): i for i, b in enumerate(batches)}
            results = {}
            first_error = None
            for future in as_completed(futures):
                idx = futures[future]
                res = future.result()
                if res.get("status") == "success":
                    results[idx] = res.get("data", {})
                elif not first_error:
                    first_error = res.get("error", "Streamer failure")

        for idx in sorted(results.keys()):
            data = results[idx]
            if not combined_response["ohlcv"]:
                combined_response["ohlcv"] = data.get("ohlcv", [])
            combined_response["indicators"].update(data.get("indicators", {}))

        if not combined_response["ohlcv"] and first_error:
            fallback_streamer = build_scraper(Streamer)
            fallback = fallback_streamer.get_candles(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                numb_candles=numb_price_candles,
            )

            if fallback.get("status") == "success":
                fallback_data = fallback.get("data", {})
                combined_response["ohlcv"] = fallback_data.get("ohlcv", [])
            else:
                return {"success": False, "errors": [first_error], "message": first_error}

        merged_data = merge_ohlc_with_indicators({
            "ohlc": combined_response["ohlcv"],
            "indicator": combined_response["indicators"]
        })

        # Keep requested indicator columns present even when upstream returns
        # OHLCV only due transient indicator stream gaps.
        expected_fields = set()
        for indicator_name in indicators:
            expected_fields.update(INDICATOR_FIELD_MAPPING.get(indicator_name, {}).values())

        if expected_fields:
            for row in merged_data:
                if "_merge_errors" in row:
                    continue
                for field_name in expected_fields:
                    row.setdefault(field_name, None)

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
