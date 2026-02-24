"""
Application runner script.

Simple script to start the FastAPI application with uvicorn.
Run this from the project root directory.
"""

import uvicorn
from backend.core.config import settings

if __name__ == "__main__":
    host = "localhost"
    port = settings.APP_PORT
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
