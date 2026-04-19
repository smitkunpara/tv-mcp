# TradingView MCP Server

A FastMCP server and HTTP API for real-time TradingView data scraping.  
Supports the **MCP protocol** (stdio) for AI assistants and a **REST API** for direct integration.

> [!WARNING]
> The **stdio (MCP)** tools are thoroughly tested and confirmed working. The **Vercel (HTTP)** endpoints are in beta and have not been fully verified for all edge cases.

## Roadmap

- [x] Migrate to `tv_scraper` V1.4.1 (modular architecture and standardized responses).
- [x] Integrate unified NSE/BSE Option Chain OI & PCR data.
- [x] Implement BSE OI scraping (SENSEX, BANKEX, SX50).

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
| Options | `get_option_chain_greeks` (TradingView-wide), `get_option_chain_oi` (NSE/BSE OI) |

---

## Documentation

| Guide | Description |
|---|---|
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

