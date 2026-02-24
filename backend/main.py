"""
FastAPI application entry point.

This module initializes and configures the FastAPI application with:
- Database initialization
- API routers
- CORS middleware
- Logging configuration
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.core.config import settings
from backend.database.initiation import InitDatabase
from backend.database.db import close_engine
from backend.api.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Manage application lifespan.

    This context manager handles:
    - Database initialization on startup
    - Resource cleanup on shutdown

    Args:
        fastapi_app: The FastAPI application instance
    """
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VER)

    try:
        logger.info("Initializing database...")
        db_init = InitDatabase()
        db_init.initialize()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise

    yield

    logger.info("Shutting down application...")
    close_engine()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VER,
    description="Financial data scraping and analysis API",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
frontend_dir = Path(__file__).parent.parent / "frontend"

app.mount(
    "/scripts",
    StaticFiles(directory=str(frontend_dir / "scripts")),
    name="scripts"
)
app.mount(
    "/styles",
    StaticFiles(directory=str(frontend_dir / "styles")),
    name="styles"
)
app.mount(
    "/pages",
    StaticFiles(directory=str(frontend_dir / "pages")),
    name="pages"
)


@app.get("/")
async def root():
    """Serve the main collection page."""
    index_file = frontend_dir / "pages" / "index.html"
    return FileResponse(index_file)


@app.get("/management")
async def management_page():
    """Serve the management page."""
    management_file = frontend_dir / "pages" / "management.html"
    return FileResponse(management_file)


@app.get("/detail")
async def detail_page():
    """Serve the detail page."""
    detail_file = frontend_dir / "pages" / "detail.html"
    return FileResponse(detail_file)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VER
    }


@app.get("/api/config")
async def get_config():
    """Get frontend configuration."""
    return {
        "apiBaseUrl": f"http://localhost:{settings.APP_PORT}/api/v1"
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting %s on port %d", settings.APP_NAME, settings.APP_PORT)

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=True,
        log_level="info"
    )
