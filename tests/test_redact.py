"""Tests for secret/PII redaction."""
from __future__ import annotations

import logging
import re

from src.core.redact import RedactionFilter, redact_string


def test_redact_api_key() -> None:
    patterns = [re.compile(r"(?i)(sk-[a-zA-Z0-9]{20,})")]
    text = "Using key sk-abcdefghijklmnopqrstu for auth"
    result = redact_string(text, patterns)
    assert "sk-" not in result
    assert "***REDACTED***" in result


def test_redact_bearer_token() -> None:
    patterns = [re.compile(r"(?i)(Bearer\s+[a-zA-Z0-9._\-]+)")]
    text = "Header: Bearer my-secret-token.123"
    result = redact_string(text, patterns)
    assert "my-secret-token" not in result
    assert "***REDACTED***" in result


def test_redact_filter_on_log_record() -> None:
    filt = RedactionFilter([r"(?i)(sk-[a-zA-Z0-9]{20,})"])
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="key=sk-abcdefghijklmnopqrstuvwxyz",
        args=None,
        exc_info=None,
    )
    filt.filter(record)
    assert "sk-" not in record.msg
    assert "***REDACTED***" in record.msg


def test_no_redaction_when_no_match() -> None:
    patterns = [re.compile(r"(?i)(sk-[a-zA-Z0-9]{20,})")]
    text = "No secrets here"
    result = redact_string(text, patterns)
    assert result == "No secrets here"
