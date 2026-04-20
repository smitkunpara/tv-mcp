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

---

## Security

| Variable | Default | Description |
|---|---|---|
| `TV_CLIENT_KEY` | `client-secret-123` | API key required for authenticated MCP HTTP/SSE access. **Change this in production.** |
| `TV_OAUTH_JWKS_URL` | *(empty)* | JWKS endpoint used to validate OAuth bearer JWTs. If set, OAuth is enabled. |
| `TV_OAUTH_ISSUER` | *(empty)* | Optional expected `iss` claim for bearer JWTs. |
| `TV_OAUTH_AUDIENCE` | *(empty)* | Optional expected `aud` claim for bearer JWTs. |
| `TV_OAUTH_REQUIRED_SCOPE` | *(empty)* | Optional required scope (from `scope` or `scp`) in bearer JWT claims. |
| `TV_OAUTH_ALGORITHMS` | `RS256` | Comma-separated JWT algorithms allowed during verification. |
| `TV_OAUTH_LEEWAY_SECONDS` | `30` | Allowed clock skew when validating token expiry/not-before claims. |

When OAuth is enabled, valid bearer tokens are accepted first and API key auth remains available as a fallback.

---

## Optional / MCP Server

| Variable | Default | Description |
|---|---|---|
| `MCP_HTTP_HOST` | `0.0.0.0` | Host bind for `tradingview-mcp-http` and `tradingview-mcp-sse` |
| `MCP_HTTP_PORT` | `8000` | Port bind for remote MCP server entrypoints |
| `MCP_HTTP_TRANSPORT` | `http` | Transport for `tradingview-mcp-http` (`http`, `streamable-http`, or `sse`) |
| `MCP_HTTP_PATH` | `/mcp` (HTTP) / `/sse` (SSE) | MCP mount path override |
| `MCP_SSE_PATH` | `/sse` | Path override used by `tradingview-mcp-sse` |
