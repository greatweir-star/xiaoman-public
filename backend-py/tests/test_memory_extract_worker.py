from xiaoman.memory.extractor import MemoryExtractor
from xiaoman.memory.store import MemoryStore


class FakeLLM:
    def complete(self, _messages):
        return {
            "choices": [
                {
                    "message": {
                        "content": '[{"content": "用户喜欢画画", "category": "preference", "layer": "L7"}]'
                    }
                }
            ]
        }


def test_extract_now_supports_durable_worker_execution(tmp_path):
    store = MemoryStore(str(tmp_path))
    extractor = MemoryExtractor(FakeLLM(), store=store)

    result = extractor.extract_now(
        user_id="user-1",
        session_id="session-1",
        messages=[{"role": "user", "content": "我喜欢画画"}],
    )

    assert result == {"processed_messages": 1, "facts": 1}
    assert store.load_facts("user-1")[0]["content"] == "用户喜欢画画"
