#!/usr/bin/env python3
"""Run MCP server standalone."""
import uvicorn
import logging
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    from mcp.server import app
    print("=" * 60)
    print("Starting MCP Server")
    print("=" * 60)
    print(f"Server URL: http://0.0.0.0:8001")
    print(f"Available servers: memory-server, tool-server")
    print(f"Health check: http://localhost:8001/health")
    print(f"List servers: http://localhost:8001/servers")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8001)
