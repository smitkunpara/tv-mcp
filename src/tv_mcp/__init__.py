"""
tv_mcp - Modular TradingView MCP service layer.

This package provides a clean, domain-driven architecture for the TradingView
MCP server with modular services, validators, and transport adapters.

Sub-packages:
    core        – settings, auth/JWT, validators, response contracts
    transforms  – data transformation utilities (time, OHLC, news)
    services    – domain service modules (historical, news, options, etc.)
    adapters    – response/contract adapters for legacy ↔ new formats
    mcp         – FastMCP server and tool definitions
"""

__version__ = "0.2.0"
__all__: list[str] = []
