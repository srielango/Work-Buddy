"""Logging configuration for Work Buddy."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(data_dir: Path) -> logging.Logger:
    """Configure application logging with rotating file and console handlers."""
    log_file = data_dir / "workbuddy.log"

    logger = logging.getLogger("workbuddy")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if called more than once
    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    ))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "[%(levelname)s] %(message)s",
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
