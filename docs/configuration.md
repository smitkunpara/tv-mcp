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

## Optional / Vercel

| Variable | Default | Description |
|---|---|---|
| `PUBLIC_APP_URL` | `https://tradingview-mcp.vercel.app` | Base URL used in the OpenAPI spec (`/openapi.json`) and root endpoint. Set this in Vercel to your **stable alias** (e.g. `https://tradingview-mcp.vercel.app`) so docs and clients use one URL instead of the deployment URL. |
| `VERCEL_URL` | *(set by Vercel)* | Deployment hostname (no scheme). Used as fallback when `PUBLIC_APP_URL` is not set. |

---

## Optional / MCP Remote Server

| Variable | Default | Description |
|---|---|---|
| `MCP_HTTP_HOST` | `0.0.0.0` | Host bind for `tradingview-mcp-http` and `tradingview-mcp-sse` |
| `MCP_HTTP_PORT` | `8000` | Port bind for remote MCP server entrypoints |
| `MCP_HTTP_TRANSPORT` | `http` | Transport for `tradingview-mcp-http` (`http`, `streamable-http`, or `sse`) |
| `MCP_HTTP_PATH` | `/mcp` (HTTP) / `/sse` (SSE) | MCP mount path override |
| `MCP_SSE_PATH` | `/sse` | Path override used by `tradingview-mcp-sse` |
