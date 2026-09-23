"""
Structured logging infrastructure for the SIH26143 pipeline.

Ensures consistent log formatting, timestamps in UTC, and log levels.
"""

import logging
import sys
import os
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Configure and return a standard logger for a module.
    Level can be overridden via LOG_LEVEL environment variable.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        log_level_str = level or os.environ.get("LOG_LEVEL", "INFO").upper()
        numeric_level = getattr(logging, log_level_str, logging.INFO)
        logger.setLevel(numeric_level)
        
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ"
        )
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger
