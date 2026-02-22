# TradingView MCP Server

A FastMCP server and HTTP API for real-time TradingView data scraping and paper trading.  
Supports the **MCP protocol** (stdio) for AI assistants and a **REST API** for direct integration.

> [!WARNING]
> The **stdio (MCP)** tools are thoroughly tested and confirmed working. The **Vercel (HTTP)** endpoints are in beta and have not been fully verified for all edge cases.

> [!WARNING]
> **Paper trading tools are in beta** (both stdio and Vercel). Behavior and APIs may change. Use with caution.

## Roadmap

- [x] Migrate to `tv_scraper` V1.0.0 (Modular architecture).
- [x] Integrate NSE Option Chain OI & PCR data (NIFTY, BANKNIFTY, etc.).
- [x] Implement paper trading mode (AI-driven simulated trading with full P&L tracking).
- [ ] Implement BSE OI scraping (pending).

---

## Quick Start

```bash
git clone https://github.com/smitkunpara/tradingview-mcp.git
cd tradingview-mcp
uv sync
cp .env.example .env   # then edit .env with your TradingView cookie
```

### MCP Server (stdio)

```bash
uv run python server.py
```

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "TradingView": {
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "env": {
        "TRADINGVIEW_COOKIE": "your_tradingview_cookies_here"
      }
    }
  }
}
```

### HTTP Server

```bash
uv run python vercel/app.py   # listens on http://localhost:4589
```

---

## Available Tools

| Category | Tools |
|---|---|
| Market Data | `get_historical_data`, `get_all_indicators` |
| News | `get_news_headlines`, `get_news_content` |
| Community | `get_ideas`, `get_minds` |
| Options | `get_option_chain_greeks`, `get_nse_option_chain_oi` |
| Paper Trading | `place_order`, `close_position`, `view_positions`, `show_capital`, `set_alert`, `alert_manager`, `view_available_alerts`, `remove_alert` |

---

## Removing paper trading tools (stdio and Vercel)

Paper trading is optional. To disable it:

### stdio (MCP server)

1. Open `src/tv_mcp/mcp/server.py`.
2. Comment out the paper trading import:
   ```python
   # from .tools.paper_trading import (
   #     place_order,
   #     close_position,
   #     ...
   # )
   ```
3. Comment out the paper trading tool registrations (the block of `mcp.tool()(place_order)` etc.).

### Vercel (HTTP API)

1. Open `vercel/app.py`.
2. Comment out the router import: `# from .routers import paper_trading`
3. Comment out the router registration: `# application.include_router(paper_trading.router)`

After these changes, the server will run without paper trading tools.

---

## Documentation

| Guide | Description |
|---|---|
| [Paper Trading Guide](docs/paper-trading-guide.md) | Full paper trading walkthrough, tools, DB, scripts |
| [Configuration Reference](docs/configuration.md) | All environment variables explained |
| [HTTP API Reference](docs/http-api.md) | REST endpoint details with examples |
| [Deployment Guide](docs/deployment.md) | Vercel, ChatGPT, cookie extension setup |

---

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Make your changes and open a pull request.

## License

MIT — see [LICENSE](LICENSE).

