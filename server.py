"""Root launcher for the TradingView MCP stdio server."""

from pathlib import Path
import sys


def _load_main():
    try:
        from tv_mcp.mcp.server import main

        return main
    except ModuleNotFoundError:
        project_root = Path(__file__).resolve().parent
        src_dir = project_root / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        from tv_mcp.mcp.server import main

        return main


main = _load_main()


if __name__ == "__main__":
    main()
