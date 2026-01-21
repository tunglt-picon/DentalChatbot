"""Main FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging
from routers import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dental Chatbot API",
    description="OpenAI-compatible API for Dental Chatbot using Ollama (free, no rate limits)",
    version="2.0.0"
)

# CORS middleware (if needed for Open WebUI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(openai.router, tags=["OpenAI Compatible"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - serve web interface."""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/config", response_class=HTMLResponse)
async def config_page():
    """Configuration page."""
    with open("templates/config.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "message": "Dental Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "models": "/v1/models",
            "chat": "/v1/chat/completions"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Configuration API
class ConfigRequest(BaseModel):
    llm_provider: str
    guardrail_provider: str
    ollama_model: Optional[str] = None
    ollama_guardrail_model: Optional[str] = None
    gemini_model: Optional[str] = None
    search_tool: str


@app.post("/api/config")
async def save_config(config: ConfigRequest):
    """Save configuration (for future use - currently just returns success)."""
    # In future, this could save to database or file
    # For now, frontend uses localStorage
    return JSONResponse(content={"status": "success", "message": "Configuration saved"})


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    import config as app_config
    return JSONResponse(content={
        "llm_provider": app_config.settings.llm_provider,
        "guardrail_provider": app_config.settings.guardrail_provider,
        "ollama_model": app_config.settings.ollama_model,
        "search_tool": "duckduckgo"  # Default
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
