# Configuration Reference

All configuration is driven by environment variables. Copy `.env.example` to `.env` and fill in your values.

---

## TradingView Connection

| Variable | Default | Description |
|---|---|---|
| `TRADINGVIEW_COOKIE` | *(required)* | Full `Cookie` header value from a logged-in TradingView session |
| `TRADINGVIEW_URL` | `https://in.tradingview.com/chart/` | Chart URL used for streaming |
| `TRADINGVIEW_USER_AGENT` | Chrome/120 UA string | Browser user-agent string |

### Getting Your Cookie

1. Visit [TradingView](https://www.tradingview.com/) and log in.
2. Open any chart and open DevTools → **Network** tab.
3. Reload the page (F5).
4. Find a GET request to `https://www.tradingview.com/chart/?symbol=...`
5. Under **Request Headers**, copy the full `Cookie` header value.
6. In `.env`, set `TRADINGVIEW_COOKIE="<paste here>"`.
7. If the cookie value contains quotes, escape them as `\"`.

You can also use the [Chrome extension](../cookie_updater_extension/README.md) to update cookies automatically.

---

## Security Keys

| Variable | Default | Description |
|---|---|---|
| `TV_ADMIN_KEY` | `admin-secret-123` | Key required for admin endpoints (e.g. `/update-cookies`). **Change this in production.** |
| `TV_CLIENT_KEY` | `client-secret-123` | Key required for client data endpoints (e.g. ChatGPT / Vercel). **Change this in production.** |

---

## Paper Trading

| Variable | Default | Description |
|---|---|---|
| `PAPER_TRADING_CAPITAL` | `100000` | Starting capital (used as default on first DB initialisation) |
| `MIN_RISK_REWARD_RATIO` | `1.5` | Minimum R:R ratio required to place a trade (DB default) |
| `MAX_OPEN_POSITIONS` | `10` | Maximum simultaneous open positions (DB default) |
| `TRAILING_SL_STEP_PCT` | `0.5` | Trailing SL step as a % of current price (DB default) |
| `ALERT_MANAGER_TIMEOUT_SECONDS` | `300` | Seconds `alert_manager` waits before timing out. Must be ≥ 0; values < 0 default to 300. |
| `INJECT_ALERTS_IN_ALL_TOOLS` | `false` | When `true`, triggered alert events are injected into every tool response |

> **Note:** Once the database exists, paper trading config is read from `trading_config` in `paper_trades.db` — not from env vars. Use [`scripts/setup_paper_trading.py`](../docs/paper-trading-guide.md#setup_paper_tradingpy) to change them.

---

## Optional / Vercel

| Variable | Default | Description |
|---|---|---|
| `VERCEL_URL` | *(empty)* | Public deployment URL, used by Vercel to set `servers[0].url` in OpenAPI spec |
