"""
Database connection and session management.
"""

from typing import Generator, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from backend.core import settings


_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Get or create the global database engine.

    This function implements lazy initialization to avoid creating
    the engine at import time, which can cause issues in testing
    and multiprocessing environments.

    Returns:
        Engine: SQLAlchemy engine instance
    """
    global _engine

    if _engine is None:
        database_url = settings.get_database_url()

        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
            isolation_level="READ COMMITTED",
            implicit_returning=False,
            connect_args={
                "fast_executemany": True,
            }
        )

    return _engine


def create_session() -> sessionmaker:
    """Create a session factory bound to the engine.

    Returns:
        sessionmaker: SQLAlchemy session factory
    """
    engine = get_engine()
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_session() -> Generator[Session, None, None]:
    """Dependency function to get database session.

    This function is used as a FastAPI dependency to provide
    database sessions to route handlers.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_session)):
            # Use db session here
            pass

    Yields:
        Session: SQLAlchemy database session
    """
    SessionLocal = create_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_engine():
    """Close the database engine and cleanup connections.

    This should be called during application shutdown.
    """
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
