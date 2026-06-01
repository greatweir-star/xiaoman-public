from app.config import Settings
from app.repositories.file import create_file_repositories
from app.services.usage import UsageService


def test_usage_service_records_and_summarizes_cost(tmp_path):
    repositories = create_file_repositories(str(tmp_path))
    service = UsageService(
        repositories.usage,
        Settings(llm_prompt_cost_per_1m=2.0, llm_completion_cost_per_1m=4.0),
    )

    record = service.record_llm_call(
        tenant_id="tenant-1",
        user_id="user-1",
        session_id="session-1",
        event={
            "provider": "test-provider",
            "model": "test-model",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "latency_ms": 42,
            "status": "success",
        },
    )

    assert record["cost_estimate"] == 0.0004
    summary = service.summarize_user("tenant-1", "user-1")
    assert summary["total_prompt_tokens"] == 100
    assert summary["total_completion_tokens"] == 50
    assert summary["total_cost_estimate"] == 0.0004
    assert summary["records"][0]["model"] == "test-model"


def test_usage_service_records_failed_call_without_tokens(tmp_path):
    service = UsageService(create_file_repositories(str(tmp_path)).usage, Settings())

    record = service.record_llm_call(
        tenant_id="tenant-1",
        user_id="user-1",
        session_id=None,
        event={"status": "error", "metadata": {"error_type": "TimeoutError"}},
    )

    assert record["status"] == "error"
    assert record["prompt_tokens"] == 0
    assert record["metadata"] == {"error_type": "TimeoutError"}
