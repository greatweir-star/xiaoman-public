"""WebSocket 流式协议辅助函数测试"""

from xiaoman.ws_protocol import (
    accumulate_stream_message,
    extract_stream_delta,
    new_stream_message_id,
)


def test_extract_stream_delta():
    chunk = {"choices": [{"delta": {"content": "你"}}]}
    assert extract_stream_delta(chunk) == "你"
    assert extract_stream_delta({}) == ""


def test_accumulate_stream_text_only():
    chunks = [
        {"choices": [{"delta": {"content": "你好"}}]},
        {"choices": [{"delta": {"content": "呀"}}]},
    ]
    msg = accumulate_stream_message(chunks)
    assert msg["content"] == "你好呀"
    assert "tool_calls" not in msg


def test_accumulate_stream_with_tool_calls():
    chunks = [
        {
            "choices": [{
                "delta": {
                    "tool_calls": [{
                        "index": 0,
                        "id": "call_1",
                        "function": {"name": "memory", "arguments": '{"'},
                    }],
                },
            }],
        },
        {
            "choices": [{
                "delta": {
                    "tool_calls": [{
                        "index": 0,
                        "function": {"arguments": 'fact": "x"}'},
                    }],
                },
            }],
        },
    ]
    msg = accumulate_stream_message(chunks)
    assert msg["tool_calls"][0]["function"]["name"] == "memory"
    assert "fact" in msg["tool_calls"][0]["function"]["arguments"]


def test_new_stream_message_id_unique():
    a = new_stream_message_id()
    b = new_stream_message_id()
    assert a != b
    assert len(a) == 16
