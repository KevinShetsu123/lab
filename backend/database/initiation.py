"""
Database initialization and setup.

This module handles database and table creation with proper error handling
and connection management.
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from backend.core.config import settings
from backend.database import Base, DatabaseExistence
# Import all models to register them with Base.metadata
from backend.database.models import (
    FinancialReport,
    BalanceSheetItem,
    IncomeStatementItem,
    CashFlowItem
)

logger = logging.getLogger(__name__)


class InitDatabase(DatabaseExistence):
    """Database initialization class."""

    def __init__(self):
        super().__init__()
        self.target_engine = None

    def _get_target_engine(self):
        """Get or create engine for target database."""
        if self.target_engine is None:
            target_url = settings.get_database_url()
            self.target_engine = create_engine(
                target_url,
                poolclass=QueuePool,
                echo=False,
                pool_pre_ping=True,
                connect_args={"fast_executemany": True}
            )
        return self.target_engine

    def create_db(self):
        """
        Create database if it doesn't exist.
        Uses master database connection to create the target database.
        """
        if self.database_exists():
            logger.info(
                "Database '%s' already exists.", self.db_name
            )
            return

        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE [{self.db_name}]"))

            logger.info("Database '%s' created successfully", self.db_name)
        except SQLAlchemyError as exc:
            logger.error(
                "Failed to create database '%s': %s",
                self.db_name,
                exc
            )
            raise

    def create_tables(self):
        """
        Create all tables defined in models if they don't exist.
        """
        if not self.database_exists():
            logger.error(
                "Database '%s' does not exist.",
                self.db_name
            )
            raise RuntimeError(f"Database '{self.db_name}' does not exist")

        try:
            logger.info("Getting target engine for table creation...")
            engine = self._get_target_engine()

            logger.info("Creating tables from Base.metadata...")
            logger.debug(
                "Tables to create: %s",
                list(Base.metadata.tables.keys())
            )

            Base.metadata.create_all(bind=engine)

            logger.info("All tables created/verified successfully")

            if self.tables_exist():
                logger.info("All required tables are present")
            else:
                logger.warning("Some tables may be missing after creation")

        except SQLAlchemyError as exc:
            logger.error("Failed to create tables: %s", exc)
            raise

    def initialize(self):
        """
        Complete database initialization: create database and tables.
        """
        logger.info("Starting database initialization...")

        try:
            if not self.connection():
                raise RuntimeError("Cannot connect to SQL Server")

            self.create_db()

            if not self.tables_exist():
                logger.info("Tables do not exist. Creating tables...")
                self.create_tables()
            else:
                logger.info("All tables already exist.")

            logger.info("Database initialization completed successfully!")
        except Exception as exc:
            logger.error("Database initialization failed: %s", exc)
            raise
        finally:

            if self.target_engine is not None:
                self.target_engine.dispose()
                logger.debug("Target engine disposed")
            if self.engine is not None:
                self.engine.dispose()
                logger.debug("Master engine disposed")
