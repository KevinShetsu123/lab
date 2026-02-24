"""
Database maintenance utilities.

This module provides utilities for database cleanup and recreation,
especially useful when tables are created in wrong database.
"""

import logging
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool
from backend.core.config import settings
from backend.database.base import Base


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseExistence:
    """Class to check database and table existence."""

    def __init__(self):
        """Initialize with settings from config."""
        self.db_name = settings.DB_NAME
        self.master_url = settings.get_master_database_url()

        self.engine = create_engine(
            self.master_url,
            poolclass=NullPool,
            isolation_level="AUTOCOMMIT",
            echo=False,
        )

    def connection(self) -> bool:
        """
        Validate database connection to SQL Server.

        Returns:
            bool: True if connection is valid, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connection to SQL Server successful")
            return True
        except SQLAlchemyError as exc:
            logger.error("Connection failed: %s", exc)
            return False

    def database_exists(self) -> bool:
        """
        Validate that target database exists on SQL Server.

        Returns:
            bool: True if database exists, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT 1 FROM sys.databases WHERE name = :db_name"
                    ),
                    {"db_name": self.db_name}
                )

                exists = result.scalar() is not None

                if exists:
                    logger.info("Database '%s' exists", self.db_name)
                else:
                    logger.warning(
                        "Database '%s' does not exist",
                        self.db_name
                    )

                return exists

        except SQLAlchemyError as exc:
            logger.error("Database existence check failed: %s", exc)
            return False

    def tables_exist(self) -> bool:
        """
        Check whether all required tables exist in the target database.

        Returns:
            bool: True if all required tables exist, False otherwise
        """
        required_tables = {
            "balance_sheet_items",
            "income_statement_items",
            "cash_flow_statement_items",
            "financial_reports",
        }

        if not self.database_exists():
            return False

        target_engine = None
        try:
            target_url = settings.get_database_url()
            target_engine = create_engine(target_url, poolclass=NullPool)

            with target_engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        SELECT TABLE_NAME
                        FROM INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_TYPE = 'BASE TABLE'
                        AND TABLE_SCHEMA = 'dbo'
                        AND TABLE_CATALOG = :db_name
                        """
                    ),
                    {"db_name": self.db_name}
                )

                existing_tables = {row[0] for row in result.fetchall()}

                logger.info(
                    "Tables found in %s: %s",
                    self.db_name,
                    existing_tables if existing_tables else "None"
                )

                missing_tables = required_tables - existing_tables

                if not missing_tables:
                    logger.info("All required tables exist")
                    return True

                logger.warning(
                    "Missing tables: %s",
                    ", ".join(sorted(missing_tables))
                )
                return False

        except SQLAlchemyError as exc:
            logger.error("Table existence check failed: %s", exc)
            return False
        finally:
            if target_engine is not None:
                target_engine.dispose()


class DatabaseMaintenance:
    """Database maintenance operations."""

    def __init__(self):
        """Initialize maintenance class."""
        self.db_name = settings.DB_NAME
        self.target_url = settings.get_database_url()
        self.target_engine = None

    def get_engine(self):
        """Get engine for target database."""
        if self.target_engine is None:
            self.target_engine = create_engine(
                self.target_url,
                poolclass=NullPool,
                isolation_level="AUTOCOMMIT",
                echo=False,
            )
        return self.target_engine

    def drop_tables(self):
        """Drop all tables from target database."""
        logger.info("Dropping tables from %s database...", self.db_name)

        try:
            engine = self.get_engine()
            with engine.connect() as conn:
                logger.info("Dropping foreign key constraints...")
                fk_query = text("""
                    SELECT
                        fk.name AS constraint_name,
                        OBJECT_NAME(fk.parent_object_id) AS table_name
                    FROM sys.foreign_keys AS fk
                """)

                fks = conn.execute(fk_query).fetchall()
                for fk in fks:
                    constraint_name = fk[0]
                    table_name = fk[1]
                    logger.info(
                        "Dropping FK constraint: %s from %s",
                        constraint_name,
                        table_name
                    )
                    conn.execute(
                        text(
                            f"ALTER TABLE [{table_name}] "
                            f"DROP CONSTRAINT [{constraint_name}]"
                        )
                    )

                # Drop all check constraints
                logger.info("Dropping check constraints...")
                chk_query = text("""
                    SELECT
                        cc.name AS constraint_name,
                        OBJECT_NAME(cc.parent_object_id) AS table_name
                    FROM sys.check_constraints AS cc
                """)

                check_constraints = conn.execute(chk_query).fetchall()
                for chk in check_constraints:
                    constraint_name = chk[0]
                    table_name = chk[1]
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE [{table_name}] "
                                f"DROP CONSTRAINT [{constraint_name}]"
                            )
                        )
                    except SQLAlchemyError:
                        pass

                drop_order = [
                    "cash_flow_statement_items",
                    "income_statement_items",
                    "balance_sheet_items",
                    "financial_reports"
                ]

                for table_name in drop_order:
                    logger.info("Dropping table: %s", table_name)
                    conn.execute(text(f"DROP TABLE IF EXISTS [{table_name}]"))
                    logger.info("Dropped: %s", table_name)

                logger.info(
                    "Successfully dropped all tables from %s",
                    self.db_name
                )

        except SQLAlchemyError as exc:
            logger.error("Failed to drop tables from target: %s", exc)
            raise

    def drop_database(self):
        """Drop all tables from the target database."""
        logger.warning("Dropping all tables from database: %s", self.db_name)
        self.drop_tables()

    def recreate_tables(self):
        """Recreate all tables in target database."""
        logger.info("Creating tables in %s...", self.db_name)
        try:
            engine = self.get_engine()
            Base.metadata.create_all(bind=engine)

            logger.info(
                "All tables created successfully in %s",
                self.db_name
            )

        except SQLAlchemyError as exc:
            logger.error("Failed to create tables: %s", exc)
            raise

    def factory_reset(self):
        """Complete database reset: drop and recreate everything."""
        logger.info("=" * 60)
        logger.info("STARTING FULL DATABASE RESET")
        logger.info("=" * 60)

        try:
            logger.info("\n[1/3] Dropping all tables...")
            self.drop_tables()

            logger.info("\n[2/3] Creating tables...")
            self.recreate_tables()

            logger.info("\n[3/3] Verifying setup...")
            self.verify_setup()
            logger.info("DATABASE RESET COMPLETED SUCCESSFULLY!")

        except Exception as exc:
            logger.error("DATABASE RESET FAILED: %s", exc)
            raise
        finally:
            self.cleanup()

    def verify_setup(self):
        """Verify database and tables exist."""
        try:
            engine = self.get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT TABLE_NAME
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_NAME
                """))

                tables = [row[0] for row in result.fetchall()]

                if tables:
                    logger.info(
                        "Tables in %s: %s", self.db_name, ", ".join(tables)
                    )
                else:
                    logger.warning("No tables found in %s", self.db_name)

        except SQLAlchemyError as exc:
            logger.error("Verification failed: %s", exc)

    def cleanup(self):
        """Cleanup database connections."""
        if self.target_engine:
            self.target_engine.dispose()


def main():
    """Run database maintenance."""
    maintenance = DatabaseMaintenance()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "Delete":
            maintenance.factory_reset()
        else:
            print(
                "Unknown command. Use: Delete"
            )
            sys.exit(1)
    else:
        print("Usage: python -m backend.database.maintenance Delete")
        sys.exit(1)


if __name__ == "__main__":
    main()
