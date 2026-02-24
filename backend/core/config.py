"""
Application configuration management.

This module loads and validates environment variables from .env file,
providing a centralized configuration object for the entire application.
"""

import urllib.parse
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings are automatically loaded from .env file at the project root.
    Missing required values will raise an error at startup.
    """

    # Application Settings
    APP_NAME: str = Field(..., description="Application name")
    APP_VER: str = Field(..., description="Application version")
    APP_PORT: int = Field(8000, description="Port number for the application")

    # Database Settings
    DB_DRIVER: str = Field(
        "ODBC Driver 18 for SQL Server",
        description="ODBC driver for SQL Server"
    )
    DB_NAME: str = Field(..., description="Database name")
    DB_HOST: str = Field(..., description="Database host")
    DB_PORT: int = Field(1433, description="Database port")
    DB_USER: str = Field(..., description="Database user")
    DB_PASSWORD: str = Field(..., description="Database password")
    DB_TRUST_CERT: str = Field("yes", description="Trust server certificate")

    # Security Settings
    SECRET_KEY: str = Field(..., description="Secret key for JWT")
    ALGORITHM: str = Field("HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        10080,
        description="Access token expiration in minutes"
    )

    # API Keys
    GEMINI_API: str = Field(..., description="Gemini API key")
    GEMINI_MODEL: str = Field(..., description="Gemini model to use")

    # LM Studio Settings
    LM_STUDIO_URL: str = Field(..., description="LM Studio API URL")
    LM_STUDIO_MODEL: str = Field(..., description="Local model for LM Studio")

    @field_validator("DB_PASSWORD", "SECRET_KEY")
    @classmethod
    def validate_not_empty(cls, value: str) -> str:
        """Validate that critical fields are not empty."""
        if not value or value.strip() == "":
            raise ValueError("Field cannot be empty")
        return value

    @field_validator("APP_PORT", "DB_PORT")
    @classmethod
    def validate_port_range(cls, value: int) -> int:
        """Validate that port numbers are in valid range."""
        if not (1 <= value <= 65535):
            raise ValueError(
                f"Port must be between 1 and 65535, got {value}"
            )
        return value

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_positive(cls, value: int) -> int:
        """Validate that value is positive."""
        if value <= 0:
            raise ValueError(f"Value must be positive, got {value}")
        return value

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Build and return the database connection URL.

        Returns:
            str: SQLAlchemy database URL
        """

        connection_string = (
            f"DRIVER={{{self.DB_DRIVER}}};"
            f"SERVER={self.DB_HOST},{self.DB_PORT};"
            f"DATABASE={self.DB_NAME};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
            f"TrustServerCertificate={self.DB_TRUST_CERT};"
        )

        params = urllib.parse.quote_plus(connection_string)
        return f"mssql+pyodbc:///?odbc_connect={params}"

    def get_master_database_url(self) -> str:
        """Build and return the master database connection URL.

        Used for checking database existence and creating new databases.

        Returns:
            str: SQLAlchemy master database URL
        """

        connection_string = (
            f"DRIVER={{{self.DB_DRIVER}}};"
            f"SERVER={self.DB_HOST},{self.DB_PORT};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
            f"TrustServerCertificate={self.DB_TRUST_CERT};"
        )

        params = urllib.parse.quote_plus(connection_string)
        return f"mssql+pyodbc:///?odbc_connect={params}&database=master"


# Global settings instance
try:
    settings = Settings()
except Exception as e:
    raise RuntimeError(
        f"Failed to load configuration. Please check your .env file: {e}"
    ) from e
