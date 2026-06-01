"""Logging redaction filter for secrets and bearer credentials."""

from __future__ import annotations

import logging
import re

REDACTED = "[REDACTED]"
_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)((?:jwt_secret|llm_api_key|openai_api_key|api_key|access_token|refresh_token|password)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
)


def redact_text(value: object) -> str:
    text = str(value)
    for pattern in _PATTERNS:
        text = pattern.sub(rf"\1{REDACTED}" if pattern.groups else REDACTED, text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = ()
        return True


def configure_redacted_logging() -> None:
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(item, RedactingFilter) for item in handler.filters):
            handler.addFilter(RedactingFilter())
