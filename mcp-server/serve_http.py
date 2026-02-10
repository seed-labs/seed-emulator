#!/usr/bin/env python3
"""Seed Emulator MCP Server (HTTP, streamable-http) with Bearer token auth.

Phase 1: dynamic operational control plane (workspace/inventory/batch ops).

Usage:
  export SEED_MCP_TOKEN=...
  export FASTMCP_HOST=0.0.0.0
  export FASTMCP_PORT=8000
  export FASTMCP_STREAMABLE_HTTP_PATH=/mcp
  export SEED_MCP_PUBLIC_URL=http://127.0.0.1:8000
  python serve_http.py
"""

from __future__ import annotations

import os
import sys

from seedops.config import load_config


def main() -> None:
    cfg = load_config(require_token=True)

    # Signal server.py to construct FastMCP with Streamable-HTTP auth settings.
    os.environ["SEED_MCP_HTTP"] = "1"

    # Import the existing server module (tools + runtime). Its FastMCP instance
    # will be constructed using the environment variables above.
    import server as seed_server  # type: ignore  # noqa: WPS433

    print(
        f"[serve_http] Starting MCP server on http://{cfg.host}:{cfg.port}{cfg.streamable_http_path} "
        f"(public_url={cfg.public_url})"
    )
    seed_server.mcp.run(transport="streamable-http")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[serve_http] Fatal: {e}", file=sys.stderr)
        raise
