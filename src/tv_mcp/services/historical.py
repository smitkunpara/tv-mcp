"""
Historical OHLCV + indicator data fetching service.

Extracted from legacy tradingview_tools.fetch_historical_data().
"""

from typing import Any, Dict, List, Optional, Tuple
import contextlib
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

from tv_scraper import Streamer  # type: ignore[import-not-found]

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


TIMEFRAME_MAP = {
    "1m": "1", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "2h": "120", "4h": "240",
    "1d": "1D", "1w": "1W", "1M": "1M",
}


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

    # Convert string to int if necessary
    try:
        numb_price_candles = int(numb_price_candles)
    except (ValueError, TypeError):
        raise ValidationError(
            f"Number of candles must be a valid integer or string that can be converted to integer. Got: {numb_price_candles}"
        )

    if numb_price_candles < 1 or numb_price_candles > 5000:
        raise ValidationError(
            f"Number of candles must be between 1 and 5000. Got: {numb_price_candles}"
        )

    indicator_ids, indicator_versions, errors, warnings = validate_indicators(indicators)
    # If there are fatal validation errors (unrecognized indicators), return
    if errors:
        return {
            "success": False,
            "data": [],
            "errors": errors,
            "message": f"Validation failed: {'; '.join(errors)}",
        }

    try:
        # If no indicators requested, just fetch without cookies/token
        if not indicator_ids:
            streamer = Streamer(export_result=False, export_type="json")

            # Capture stdout to prevent print statements from corrupting JSON
            with contextlib.redirect_stdout(io.StringIO()):
                result = streamer.get_candles(
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=TIMEFRAME_MAP.get(timeframe, timeframe),
                    numb_candles=numb_price_candles,
                    indicators=None,
                )

            # Unwrap envelope
            if result.get("status") == "failed":
                raise ValueError(result.get("error", "Streamer returned failure"))
            data = result.get("data", {})
            merged_data = merge_ohlc_with_indicators(
                {"ohlc": data.get("ohlcv", []), "indicator": data.get("indicators", {})}
            )
            return {
                "success": True,
                "data": merged_data,
                "errors": errors,
                "metadata": {
                    "exchange": exchange,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "candles_count": len(merged_data),
                    "indicators": indicators,
                },
            }

        # Check if cookies are set then we can fetch the indicators
        if not settings.TRADINGVIEW_COOKIE:
            raise ValidationError(
                "Account is not connected with MCP. Please set TRADINGVIEW_COOKIE to fetch indicators. "
                "environment variable to connect your account."
            )

        # Batch indicators into groups of 2 (free account limit)
        BATCH_SIZE = 2
        # Create list of tuples: [(indicator_id, version), ...]
        indicator_tuples = list(zip(indicator_ids, indicator_versions))
        batched_tuples = [
            indicator_tuples[i : i + BATCH_SIZE]
            for i in range(0, len(indicator_tuples), BATCH_SIZE)
        ]

        combined_response: Dict[str, Any] = {"ohlcv": [], "indicators": {}}
        fetch_errors: List[str] = []

        def fetch_batch(
            batch_index: int, batch_tuples: List[Tuple[str, str]]
        ) -> Tuple[int, Optional[Dict], Optional[str]]:
            """Fetch a single batch of indicators in a thread.

            Returns:
                Tuple of (batch_index, response_data, error_message)
            """
            try:
                # For subsequent batches, request one extra candle per previous batch
                extra = batch_index  # 0 for first batch, 1 for second, etc.
                fetch_candles = numb_price_candles + extra

                # Generate fresh token for this batch
                try:
                    batch_token = get_valid_jwt_token()
                except ValueError as e:
                    return (batch_index, None, f"Token generation failed: {str(e)}")

                # Create a fresh Streamer per batch
                batch_streamer = Streamer(
                    export_result=False,
                    export_type="json",
                    websocket_jwt_token=batch_token,
                )

                # Capture stdout to prevent print statements from corrupting JSON
                with contextlib.redirect_stdout(io.StringIO()):
                    result = batch_streamer.get_candles(
                        exchange=exchange,
                        symbol=symbol,
                        timeframe=TIMEFRAME_MAP.get(timeframe, timeframe),
                        numb_candles=fetch_candles,
                        indicators=batch_tuples,
                    )

                # Unwrap envelope
                if result.get("status") == "failed":
                    return (batch_index, None, f"Batch {batch_index} failed: {result.get('error', 'unknown')}")
                resp = result.get("data", {})

                return (batch_index, resp, None)
            except Exception as e:
                return (batch_index, None, f"Batch {batch_index} failed: {str(e)}")

        # Use ThreadPoolExecutor to fetch batches in parallel
        with ThreadPoolExecutor(max_workers=len(batched_tuples)) as executor:
            # Submit all batch fetch tasks
            future_to_batch = {
                executor.submit(fetch_batch, idx, bt): idx
                for idx, bt in enumerate(batched_tuples)
            }

            # Collect results as they complete
            batch_results: Dict[int, Dict] = {}
            for future in as_completed(future_to_batch):
                batch_index, resp, error = future.result()

                if error:
                    fetch_errors.append(error)
                    continue

                batch_results[batch_index] = resp

        # Process results in order
        for batch_index in sorted(batch_results.keys()):
            resp = batch_results[batch_index]

            # Save OHLCV from the first response only
            if not combined_response["ohlcv"]:
                combined_response["ohlcv"] = resp.get("ohlcv") or []

            # Merge indicator arrays: append entries for each tradingview key
            for ind_key, ind_values in (resp.get("indicators") or {}).items():
                if ind_key not in combined_response["indicators"]:
                    combined_response["indicators"][ind_key] = []
                # Append new values; allow duplicates — merge function will match by timestamp
                combined_response["indicators"][ind_key].extend(ind_values or [])

            # Collect any errors returned by the streamer resp
            if isinstance(resp, dict) and resp.get("errors"):
                fetch_errors.extend(resp.get("errors") or [])

        # Ensure we have an ohlcv list
        if not combined_response.get("ohlcv"):
            raise ValueError(
                "Failed to fetch OHLC data from TradingView across batches."
            )

        # Do not convert timestamps here; merge_ohlc_with_indicators will handle datetime conversion
        # merge_ohlc_with_indicators expects keys "ohlc" and "indicator"
        merged_data = merge_ohlc_with_indicators(
            {"ohlc": combined_response["ohlcv"], "indicator": combined_response["indicators"]}
        )

        # If merge appended a final entry with _merge_errors, extract them
        merge_errors: List[str] = []
        if (
            merged_data
            and isinstance(merged_data[-1], dict)
            and "_merge_errors" in merged_data[-1]
        ):
            merge_errors = merged_data[-1].get("_merge_errors", [])
            merged_data = merged_data[:-1]

        all_errors = errors + fetch_errors + merge_errors

        return {
            "success": True,
            "data": merged_data,
            "errors": all_errors,
            "warnings": warnings,
            "metadata": {
                "exchange": exchange,
                "symbol": symbol,
                "timeframe": timeframe,
                "candles_count": len(merged_data),
                "indicators": indicators,
                "batches": len(batched_tuples),
            },
        }

    except ValueError as e:
        return {
            "success": False,
            "data": [],
            "errors": errors + [str(e)],
            "message": f"Data processing error: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "errors": errors + [f"TradingView API error: {str(e)}"],
            "message": f"Failed to fetch data from TradingView: {str(e)}",
        }
