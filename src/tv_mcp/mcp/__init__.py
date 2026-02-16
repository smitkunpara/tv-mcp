"""
MCP transport layer.

Modules:
    server      – FastMCP app factory and tool registration
    serializers – TOON encoder/decoder helpers
    tools/      – per-domain tool handler modules
"""

from .server import main, mcp

__all__ = ["main", "mcp"]
