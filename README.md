# TradingView MCP Server

FastMCP server for TradingView data with an authenticated SSE endpoint for remote clients.

This repository is configured for SSE-first deployment on Vercel.

## Quick Start

```bash
git clone https://github.com/smitkunpara/tradingview-mcp.git
cd tradingview-mcp
uv sync
cp .env.example .env
```

Set required values in `.env`:

- `TRADINGVIEW_COOKIE`
- `TV_CLIENT_KEY`

## Run Local SSE Server

```bash
export TV_CLIENT_KEY="your-client-key"
uv run tradingview-mcp-sse
```

Defaults:

- Host: `0.0.0.0`
- Port: `8000`
- SSE endpoint: `/sse`
- Health endpoint: `/health`

Optional overrides:

```bash
export MCP_HTTP_HOST="0.0.0.0"
export MCP_HTTP_PORT="8000"
export MCP_SSE_PATH="/sse"
```

Authentication headers accepted on SSE endpoint:

- `X-API-Key: <TV_CLIENT_KEY>`
- `X-Client-Key: <TV_CLIENT_KEY>`
- `Authorization: Bearer <TV_CLIENT_KEY>`

## Available Tools

| Category | Tools |
|---|---|
| Market Data | `get_historical_data`, `get_all_indicators` |
| News | `get_news_headlines`, `get_news_content` |
| Community | `get_ideas`, `get_minds` |
| Options | `get_option_chain_greeks`, `get_option_chain_oi` |

## Documentation

| Guide | Description |
|---|---|
| [Configuration Reference](docs/configuration.md) | Environment variables and runtime configuration |
| [Deployment Guide](docs/deployment.md) | SSE deployment on Vercel |

## License

MIT — see [LICENSE](LICENSE).

