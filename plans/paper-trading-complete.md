## Plan Complete: Paper Trading System

A full paper trading engine has been added to the TradingView MCP server, providing 8 new MCP tools for placing orders, monitoring positions with background screeners, managing alerts, and tracking capital. The system uses SQLite for closed trade persistence, asyncio for concurrent position monitoring, and supports trailing stop-losses with configurable risk management via environment variables. Vercel REST endpoints are included in a separately commentable file.

**Phases Completed:** 10 of 10
1. ✅ Phase 1: Settings & DB Foundation
2. ✅ Phase 2: Order Placement & Risk Management
3. ✅ Phase 3: Screener & Position Monitoring
4. ✅ Phase 4: Close Position, View Positions, Show Capital
5. ✅ Phase 5: Alert System
6. ✅ Phase 6: Alert Manager
7. ✅ Phase 7: MCP Tool Handlers
8. ✅ Phase 8: Vercel REST Endpoints
9. ✅ Phase 9: Comprehensive Tests
10. ✅ Phase 10: Integration Wiring & Validation

**All Files Created/Modified:**
- src/tv_mcp/services/paper_trading.py (new ~500 lines)
- src/tv_mcp/mcp/tools/paper_trading.py (new)
- src/tv_mcp/mcp/server.py (modified)
- src/tv_mcp/core/settings.py (modified)
- src/tv_mcp/services/__init__.py (modified)
- src/tv_mcp/mcp/tools/__init__.py (modified)
- vercel/routers/paper_trading.py (new)
- vercel/schemas.py (modified)
- vercel/app.py (modified)
- vercel/routers/public.py (modified)
- pyproject.toml (modified)
- tests/stdio/test_service_paper_trading.py (new)
- tests/stdio/test_paper_trading_tools.py (new)
- tests/http/test_paper_trading_routes.py (new)
- tests/stdio/test_mcp_server.py (modified)
- tests/stdio/test_scaffold_imports.py (modified)
- tests/http/test_scaffold_imports.py (modified)
- tests/test_entrypoint_compatibility.py (modified)

**Key Functions/Classes Added:**
- PaperTradingEngine (singleton) — core engine with positions, alerts, capital
- Position — dataclass for open positions with to_dict()
- place_order() — validates risk:reward, side inference, capital check
- _screener_loop() / _price_only_monitor() — background asyncio price monitoring
- close_position() / _close_position_internal() — manual/automatic position closing
- _record_closed_trade() — SQLite persistence for closed trades
- view_positions() — filter by open/closed/all or order_id
- show_capital() — capital summary with PnL tracking
- set_alert() / remove_alert() / view_available_alerts() — price & time alerts
- alert_manager() — blocking alert consumer (SL/target hits, price alerts, timers)
- 8 MCP tool handler functions (place_order, close_position, etc.)
- 8 Vercel REST endpoint handlers

**Test Coverage:**
- Total tests written: 65 new + 4 existing updated
- All tests passing: ✅ (298 passed, 2 pre-existing failures unrelated to changes)

**Recommendations for Next Steps:**
- Consider adding exception-path tests for MCP tool handlers (generic Exception branch)
- Review the capital accounting model (capital not deducted at order placement)
- Fix pre-existing test_vercel_init_exports and test_real_spot_price failures
- Add WebSocket-based price monitoring as a future enhancement for lower latency
