"""Structured logging module for the Healthcare Data Pipeline.

Logs structured milestone events to both logs/pipeline.log and sys.stdout.
"""
import logging
import sys
from pathlib import Path
from src.config import LOG_FILE_PATH, LOGS_DIR


def get_logger(name: str = "healthcare_pipeline") -> logging.Logger:
    """Returns a configured logger instance writing to logs/pipeline.log and stdout."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File Handler
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
