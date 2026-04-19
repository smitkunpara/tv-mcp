# HTTP API Reference

The FastAPI server exposes the same functionality as the MCP tools over REST.

**Base URL (local):** `http://localhost:4589`  
**Docs UI:** `http://localhost:4589/docs`

Start the server:
```bash
uv run python vercel/app.py
```

---

## Authentication

Protected endpoints require one of two keys passed as a header:

| Header | Key Variable | Used By |
|---|---|---|
| `X-Admin-Key` | `TV_ADMIN_KEY` | Admin endpoints |
| `X-Client-Key` | `TV_CLIENT_KEY` | Client / data endpoints |

---

## Data Endpoints

### `POST /historical-data`
Fetch historical OHLCV candles with optional technical indicators.

```json
{
  "exchange": "NSE",
  "symbol": "NIFTY",
  "timeframe": "1d",
  "numb_price_candles": 100,
  "indicators": ["RSI", "MACD"]
}
```

Timeframes: `1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M`  
Indicators: `RSI, MACD, CCI, BB`

---

### `POST /news-headlines`
Get latest news headlines from TradingView.

```json
{
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "provider": "all",
  "area": "world"
}
```

---

### `POST /news-content`
Fetch full article text for one or more story IDs (returned by `/news-headlines`).

```json
{ "story_ids": ["abc123", "def456"] }
```

---

### `POST /ideas`
Scrape community trading ideas.

```json
{
  "symbol": "BTCUSD",
  "exchange": "BITSTAMP",
  "sort": "popular",
  "startPage": 1,
  "endPage": 2
}
```

---

### `POST /minds`
Get community discussions (TradingView Minds).

```json
{
  "symbol": "NIFTY",
  "exchange": "NSE",
  "limit": 5
}
```

---

### `POST /option-chain-greeks`
Fetch option chain with Delta, Gamma, Theta, Vega, IV.

```json
{
  "symbol": "NIFTY",
  "exchange": "NSE",
  "expiry_date": "nearest",
  "no_of_ITM": 5,
  "no_of_OTM": 5
}
```

---

### `POST /option-chain-oi`
NSE/BSE Open Interest + Put-Call Ratio.

Use exchange-aware inputs with ISO expiry date.

```json
{
  "exchange": "NSE",
  "symbol": "BANKNIFTY",
  "expiry_date": "2026-02-19"
}
```

---

## Admin Endpoints

### `POST /update-cookies`
Update TradingView cookies at runtime without redeploying.

```bash
curl -X POST "https://your-app.vercel.app/update-cookies" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: <your-admin-key>" \
  -d '{"cookies": [{"name": "sessionid", "value": "..."}], "source": "extension"}'
```

---

## Public Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | API info and endpoint listing |
| `GET` | `/openapi.json` | OpenAPI 3.x specification |
| `GET` | `/privacy-policy` | Privacy policy and disclaimer |
