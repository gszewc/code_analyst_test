"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from .config import settings


def setup_logging() -> None:
    """
    Configure application logging with console and file handlers.

    Sets up:
    - Console handler with colored output for development
    - Rotating file handler for production logs
    - Structured log format with timestamp, level, logger name, and message
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (rotating, max 10MB, keep 5 backups)
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(getattr(logging, settings.log_level))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={settings.log_level}, file={settings.log_file}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
