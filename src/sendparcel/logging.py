"""Structured logging for sendparcel.

Provides JSON-formatted logging with consistent fields:
- timestamp (ISO 8601)
- level
- logger name
- message
- extra context (module, function, shipment_id, etc.)

Usage::

    from sendparcel.logging import get_logger

    logger = get_logger()
    logger.info("Shipment created", shipment_id="abc-123", provider="inpost")

In production, the JSON formatter outputs one-line JSON records suitable
for structured log aggregation (Datadog, CloudWatch, ELK, etc.).
In development, falls back to human-readable format.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


def _format_extra(extra: dict[str, Any] | None) -> dict[str, Any]:
    """Convert extra fields to a serializable dict."""
    if not extra:
        return {}
    result: dict[str, Any] = {}
    for k, v in extra.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            result[k] = v
        else:
            result[k] = str(v)
    return result


class _JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Outputs one-line JSON records with consistent fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        extra = _format_extra(getattr(record, "extra", None))
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if extra:
            log_entry["extra"] = extra
        if hasattr(record, "exc_info") and record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


class _HumanFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        extra = _format_extra(getattr(record, "extra", None))
        extra_str = " ".join(f"{k}={v}" for k, v in extra.items())
        msg = record.getMessage()
        if extra_str:
            msg = f"{msg} {extra_str}"
        return super().format(record)


def _configure_structured_logging(
    level: int = logging.INFO,
    json_format: bool | None = None,
) -> None:
    """Configure structured logging for the sendparcel package.

    Args:
        level: Logging level (default: INFO).
        json_format: Force JSON format (True/False). If None, uses
            JSON in production (LOG_LEVEL env var set), human-readable
            in development.
    """
    if json_format is None:
        json_format = os.environ.get("SENDPARCEL_LOG_FORMAT") == "json"

    for name in ("sendparcel", "sendparcel_inpost", "sendparcel_django"):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False

        # Avoid adding handlers multiple times
        if logger.handlers:
            continue

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            _JsonFormatter() if json_format else _HumanFormatter()
        )
        logger.addHandler(handler)


def get_logger(
    name: str | None = None,
    *,
    extra: dict[str, Any] | None = None,
) -> logging.LoggerAdapter:
    """Get a structured logger for the sendparcel ecosystem.

    Args:
        name: Logger name. Defaults to the caller's module name.
        extra: Extra fields to include in every log record.

    Returns:
        A LoggerAdapter with consistent structured logging.

    Usage::

        logger = get_logger()
        logger.info("Shipment created", shipment_id="abc-123")
        logger.error("API failed", exc_info=True)
    """
    # Auto-detect caller module if not specified
    if name is None:
        import inspect

        frame = inspect.currentframe()
        if frame is not None:
            caller = frame.f_back
            if caller is not None:
                name = caller.f_globals.get("__name__", __name__)

    logger = logging.getLogger(name)
    adapter = logging.LoggerAdapter(logger, extra=extra or {})
    return adapter


# Configure on first import.
_configure_structured_logging()
