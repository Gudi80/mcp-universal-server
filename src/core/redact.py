"""Redaction filter for secrets and PII in log output."""
from __future__ import annotations

import logging
import re

_REDACTED = "***REDACTED***"


class RedactionFilter(logging.Filter):
    """Logging filter that replaces secret patterns with a redaction marker."""

    def __init__(self, patterns: list[str]) -> None:
        super().__init__()
        self._compiled = [re.compile(p) for p in patterns]

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact(str(a)) for a in record.args)
        return True

    def _redact(self, text: str) -> str:
        for pattern in self._compiled:
            text = pattern.sub(_REDACTED, text)
        return text


def redact_string(text: str, patterns: list[re.Pattern[str]]) -> str:
    """Apply redaction patterns to a string."""
    for pattern in patterns:
        text = pattern.sub(_REDACTED, text)
    return text
