"""Configuration module for Apple Health Ingester.

Loads and validates environment variables for the application.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)


class Config:
    """Application configuration loaded from environment variables."""

    # Required settings
    INFLUXDB_URL: str = os.getenv("INFLUXDB_URL", "")
    INFLUXDB_TOKEN: str = os.getenv("INFLUXDB_TOKEN", "")
    INFLUXDB_ORG: str = os.getenv("INFLUXDB_ORG", "")

    # Optional settings with defaults
    INFLUXDB_BUCKET: str = os.getenv("INFLUXDB_BUCKET", "applehealth")
    API_KEY: str = os.getenv("API_KEY", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    PORT: int = int(os.getenv("PORT", "8080"))

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present.

        Returns:
            True if configuration is valid, False otherwise.
        """
        missing = []

        if not cls.INFLUXDB_URL:
            missing.append("INFLUXDB_URL")
        if not cls.INFLUXDB_TOKEN:
            missing.append("INFLUXDB_TOKEN")
        if not cls.INFLUXDB_ORG:
            missing.append("INFLUXDB_ORG")

        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            return False

        return True

    @classmethod
    def log_config(cls) -> None:
        """Log configuration summary (excluding sensitive values)."""
        logger.info("Configuration loaded:")
        logger.info(f"  INFLUXDB_URL: {cls.INFLUXDB_URL}")
        logger.info(f"  INFLUXDB_ORG: {cls.INFLUXDB_ORG}")
        logger.info(f"  INFLUXDB_BUCKET: {cls.INFLUXDB_BUCKET}")
        logger.info(f"  API_KEY: {'configured' if cls.API_KEY else 'not configured'}")
        logger.info(f"  LOG_LEVEL: {cls.LOG_LEVEL}")
        logger.info(f"  PORT: {cls.PORT}")


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
