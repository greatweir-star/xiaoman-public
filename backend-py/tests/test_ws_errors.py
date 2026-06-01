from app.ws.errors import AUTH_FAILED, INVALID_MESSAGE, MODEL_ERROR, RATE_LIMITED, ws_error_payload


def test_websocket_error_payload_has_stable_code_and_details():
    payload = ws_error_payload(RATE_LIMITED, "slow down", retryAfterSeconds=12)

    assert payload == {
        "code": "rate_limited",
        "message": "slow down",
        "retryAfterSeconds": 12,
    }
    assert {AUTH_FAILED, INVALID_MESSAGE, MODEL_ERROR, RATE_LIMITED} == {
        "auth_failed",
        "invalid_message",
        "model_error",
        "rate_limited",
    }
