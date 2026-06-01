import logging

from app.security.redaction import RedactingFilter, redact_text


def test_redact_text_removes_bearer_keys_and_jwt():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature"
    value = redact_text(f"Authorization: Bearer secret-token api_key=secret {jwt}")

    assert "secret-token" not in value
    assert "api_key=secret" not in value
    assert jwt not in value
    assert value.count("[REDACTED]") == 3


def test_redacting_filter_rewrites_formatted_log_message():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "password=%s", ("secret",), None)

    assert RedactingFilter().filter(record)
    assert record.getMessage() == "password=[REDACTED]"
