"""
Central API Router.

This module aggregates all API endpoint routers into a single router
that is included in the main FastAPI application.
"""

from fastapi import APIRouter
from backend.api.endpoints import scrapper, financial, extraction

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include endpoint routers
api_router.include_router(scrapper.router)
api_router.include_router(financial.router)
api_router.include_router(extraction.router)
