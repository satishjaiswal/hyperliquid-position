"""
Logging configuration for the Hyperliquid position monitor.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


def setup_logging(log_level: str = "INFO", log_directory: str = "logs") -> None:
    """
    Setup comprehensive logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_directory: Directory to store log files
    """
    
    # Create log directory if it doesn't exist
    log_dir = Path(log_directory)
    log_dir.mkdir(exist_ok=True)
    
    # Define log file path
    log_file = log_dir / "hyperliquid_monitor.log"
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")


class ColoredConsoleHandler(logging.StreamHandler):
    """Console handler with colored output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    
    RESET = '\033[0m'
    
    def emit(self, record):
        """Emit a colored log record."""
        try:
            msg = self.format(record)
            color = self.COLORS.get(record.levelname, '')
            colored_msg = f"{color}{msg}{self.RESET}"
            
            stream = self.stream
            stream.write(colored_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_log_level(level: str) -> None:
    """
    Change the log level for all loggers.
    
    Args:
        level: New log level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))
