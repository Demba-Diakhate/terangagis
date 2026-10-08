"""MCP minimal stub (stdio) pour TerangaGIS."""
from __future__ import annotations
import sys
class MCPServer:
    def run(self) -> None:
        sys.stdout.write('terangagis-mcp-ready\n')
