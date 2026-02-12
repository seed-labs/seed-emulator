from __future__ import annotations

import os
from urllib.parse import urlparse
from dataclasses import dataclass
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    val = os.environ.get(name)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None or val == "":
        return default
    v = val.strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _env_csv(name: str) -> list[str]:
    raw = os.environ.get(name) or ""
    if not raw.strip():
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _ensure_leading_slash(path: str) -> str:
    if not path:
        return "/"
    return path if path.startswith("/") else f"/{path}"


def get_mcp_server_dir() -> Path:
    # .../mcp-server/seedops/config.py -> .../mcp-server
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class SeedOpsConfig:
    token: str | None
    db_path: str
    data_dir: str
    public_url: str
    host: str
    port: int
    streamable_http_path: str
    dns_rebinding_protection: bool
    allowed_hosts: list[str]
    allowed_origins: list[str]


def load_config(*, require_token: bool = False) -> SeedOpsConfig:
    """Load SeedOps configuration from environment variables.

    Environment variables:
      - SEED_MCP_TOKEN
      - SEEDOPS_DB_PATH
      - SEEDOPS_DATA_DIR
      - SEED_MCP_PUBLIC_URL
      - SEED_MCP_DNS_REBINDING_PROTECTION
      - SEED_MCP_ALLOWED_HOSTS (comma-separated, e.g. "seed-mcp.example.com:*,10.0.0.5:*")
      - SEED_MCP_ALLOWED_ORIGINS (comma-separated, e.g. "http://seed-mcp.example.com:*,http://10.0.0.5:*")
      - FASTMCP_HOST
      - FASTMCP_PORT
      - FASTMCP_STREAMABLE_HTTP_PATH
    """
    mcp_server_dir = get_mcp_server_dir()
    seedops_dir = mcp_server_dir / ".seedops"

    host = os.environ.get("FASTMCP_HOST", "127.0.0.1")
    port = _env_int("FASTMCP_PORT", 8000)
    streamable_http_path = _ensure_leading_slash(os.environ.get("FASTMCP_STREAMABLE_HTTP_PATH", "/mcp"))

    token = os.environ.get("SEED_MCP_TOKEN") or None
    if require_token and not token:
        raise ValueError("SEED_MCP_TOKEN is required to run the HTTP MCP server.")

    db_path = os.environ.get("SEEDOPS_DB_PATH") or str(seedops_dir / "seedops.db")
    data_dir = os.environ.get("SEEDOPS_DATA_DIR") or str(seedops_dir / "workspaces")

    public_url = os.environ.get("SEED_MCP_PUBLIC_URL") or f"http://127.0.0.1:{port}"

    dns_rebinding_protection = _env_bool("SEED_MCP_DNS_REBINDING_PROTECTION", True)
    extra_allowed_hosts = _env_csv("SEED_MCP_ALLOWED_HOSTS")
    extra_allowed_origins = _env_csv("SEED_MCP_ALLOWED_ORIGINS")

    # Transport security allowlists:
    # - Always include localhost defaults
    # - Also include the hostname from public_url so remote clients can connect
    allowed_hosts: set[str] = {"127.0.0.1:*", "localhost:*", "[::1]:*"}
    allowed_origins: set[str] = {"http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"}
    try:
        parsed = urlparse(public_url)
        hostname = parsed.hostname
        scheme = parsed.scheme or "http"
        if hostname:
            host_for_header = f"[{hostname}]" if ":" in hostname else hostname
            allowed_hosts.add(f"{host_for_header}:*")
            allowed_origins.add(f"{scheme}://{host_for_header}:*")
    except Exception:
        # If public_url is malformed, keep safe localhost defaults and rely on explicit env overrides.
        pass

    allowed_hosts.update(extra_allowed_hosts)
    allowed_origins.update(extra_allowed_origins)

    return SeedOpsConfig(
        token=token,
        db_path=db_path,
        data_dir=data_dir,
        public_url=public_url,
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
        dns_rebinding_protection=dns_rebinding_protection,
        allowed_hosts=sorted(allowed_hosts),
        allowed_origins=sorted(allowed_origins),
    )
