"""Tiny local MCP server for testing Pantheon Integrations.

Configure it in Settings -> Integrations -> MCP with:
  Command: python
  Arguments: examples/mcp_demo_server.py
  Working directory: the Pantheon project root
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Pantheon demo tools")


@mcp.tool()
def greet(name: str) -> str:
    """Return a short greeting for a person."""
    return f"Hello from Pantheon MCP, {name}!"


@mcp.tool()
def add_numbers(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


if __name__ == "__main__":
    mcp.run(transport="stdio")
