# Deployment Guide

## Vercel

Deploy the SSE MCP server to Vercel.

**Entrypoint:** `vercel/app.py`

### Required Environment Variables

Set these in your Vercel project settings:

| Variable | Description |
|---|---|
| `TRADINGVIEW_COOKIE` | TradingView session cookie |
| `TV_CLIENT_KEY` | Client API key |
| `MCP_SSE_PATH` | Optional SSE mount path override (default `/sse`) |

### Deploying

```bash
vercel --prod
```

The `vercel.json` at the project root configures the build.

After deploy:

- Health check: `GET /health`
- SSE MCP endpoint: `GET /sse/` (or your overridden `MCP_SSE_PATH`)
- SSE message endpoint: `POST /sse/messages/?session_id=...`

---

## Client Connection Notes

For authenticated access, clients must send one of:

- `X-API-Key: <TV_CLIENT_KEY>`
- `X-Client-Key: <TV_CLIENT_KEY>`
- `Authorization: Bearer <TV_CLIENT_KEY>`

TradingView cookies are managed manually via environment variables.
