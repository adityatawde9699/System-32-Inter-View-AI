"""
InterView AI - FastAPI Application.

Main FastAPI app that serves the API and static frontend files.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.core.config import configure_logging
from src.api.routes import router as api_router


# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="InterView AI",
        description="Real-Time AI Career Coach API",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # CORS middleware for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router)
    
    # Serve static frontend files
    frontend_path = Path(__file__).parent.parent.parent / "frontend"
    if frontend_path.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    # Serve index.html at root
    @app.get("/")
    async def serve_frontend():
        index_path = frontend_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"message": "InterView AI API is running. Frontend not found."}
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 InterView AI API starting...")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("👋 InterView AI API shutting down...")
    
    return app


# Create app instance
app = create_app()
