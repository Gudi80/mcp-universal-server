"""Structured JSON logging setup for audit trail."""
from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from src.core.redact import RedactionFilter


def setup_logging(redact_patterns: list[str] | None = None) -> logging.Logger:
    """Configure and return the application logger with JSON formatting and redaction."""
    logger = logging.getLogger("mcp_server")
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)

    if redact_patterns:
        handler.addFilter(RedactionFilter(redact_patterns))

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
