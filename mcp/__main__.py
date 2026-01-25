"""Entry point for running MCP server standalone."""
import uvicorn
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    from .server import app
    uvicorn.run(app, host="0.0.0.0", port=8001)
