"""
Logging utilities for the trading bot.

Provides structured logging with file rotation and sanitization of sensitive data.
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


class SanitizingFormatter(logging.Formatter):
    """Custom formatter that sanitizes sensitive data from log messages."""

    # Patterns for sensitive data
    PATTERNS = [
        (re.compile(r'("api_key":\s*")[^"]+(")', re.IGNORECASE), r'\1***REDACTED***\2'),
        (re.compile(r'("api_secret":\s*")[^"]+(")', re.IGNORECASE), r'\1***REDACTED***\2'),
        (re.compile(r'(api_key=)[^\s,)]+', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(api_secret=)[^\s,)]+', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(COINBASE_API_KEY=)[^\s]+', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(COINBASE_API_SECRET=)[^\s]+', re.IGNORECASE), r'\1***REDACTED***'),
    ]

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sensitive data sanitization."""
        # Format the message normally
        message = super().format(record)

        # Sanitize sensitive patterns
        for pattern, replacement in self.PATTERNS:
            message = pattern.sub(replacement, message)

        return message


def setup_logger(
    name: str,
    log_dir: Path = Path("logs"),
    level: str = "INFO",
    console_output: bool = True,
    max_log_files: int = 30
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        name: Logger name (typically __name__ from calling module)
        log_dir: Directory for log files
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Whether to output to console
        max_log_files: Maximum number of log files to keep (0 = unlimited)

    Returns:
        Configured logger instance
    """
    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Clean old log files if needed
    if max_log_files > 0:
        _cleanup_old_logs(log_dir, max_log_files)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = log_dir / f"trading_bot_{timestamp}.log"

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter with sanitization
    formatter = SanitizingFormatter(
        fmt='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (optional)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    # Log startup information
    logger.info("=" * 60)
    logger.info("TRADING BOT SESSION STARTED")
    logger.info(f"Log file: {log_filename}")
    logger.info(f"Log level: {level}")
    logger.info("=" * 60)

    return logger


def _cleanup_old_logs(log_dir: Path, max_files: int) -> None:
    """
    Remove old log files, keeping only the most recent ones.

    Args:
        log_dir: Directory containing log files
        max_files: Maximum number of log files to keep
    """
    # Get all log files sorted by modification time (oldest first)
    log_files = sorted(
        log_dir.glob("trading_bot_*.log"),
        key=lambda p: p.stat().st_mtime
    )

    # Remove oldest files if we exceed the limit
    files_to_remove = len(log_files) - max_files + 1  # +1 for the new file about to be created
    if files_to_remove > 0:
        for log_file in log_files[:files_to_remove]:
            try:
                log_file.unlink()
            except Exception:
                # Silently ignore errors during cleanup
                pass


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger by name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
