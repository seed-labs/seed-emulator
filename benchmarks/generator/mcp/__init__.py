"""MCP transport adapters for vendor-neutral structured scene translation."""

from generator.mcp.contract import MCP_CONTRACT_VERSION, MCP_TOOL_NAME
from generator.mcp.profile import MCPProfile, builtin_profile
from generator.mcp.provider import MCPProvider

__all__ = [
    "MCP_CONTRACT_VERSION",
    "MCP_TOOL_NAME",
    "MCPProfile",
    "MCPProvider",
    "builtin_profile",
]
