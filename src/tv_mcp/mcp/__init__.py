"""
MCP transport layer.

Modules:
    server      – FastMCP app factory and tool registration
    serializers – TOON encoder/decoder helpers
    tools/      – per-domain tool handler modules
"""

def __getattr__(name: str):
    if name == "main":
        from .server import main

        return main
    if name == "mcp":
        from .server import mcp

        return mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["main", "mcp"]
