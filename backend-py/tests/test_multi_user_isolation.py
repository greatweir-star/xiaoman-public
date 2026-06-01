from concurrent.futures import ThreadPoolExecutor

from app.repositories.file import create_file_repositories
from app.services.dialogue import DialoguePersistenceService
from app.services.rate_limit import MemoryRateLimitBackend, RateLimitService
from app.services.usage import UsageService
from xiaoman.chunk import user_text_chunk


def test_parallel_users_keep_dialogue_usage_and_limits_isolated(tmp_path):
    repositories = create_file_repositories(str(tmp_path))
    dialogue = DialoguePersistenceService(repositories)
    usage = UsageService(repositories.usage)
    limiter = RateLimitService(MemoryRateLimitBackend(), limit=1, window_seconds=60)
    contexts = {
        user_id: dialogue.open_context(tenant_id="tenant-1", user_id=user_id)
        for user_id in ("user-a", "user-b")
    }

    def send(user_id):
        context = contexts[user_id]
        assert limiter.check(tenant_id=context.tenant_id, user_id=user_id).allowed
        dialogue.append_chunk(context, user_text_chunk(f"hello from {user_id}"))
        usage.record_llm_call(
            tenant_id=context.tenant_id,
            user_id=user_id,
            session_id=context.session_id,
            event={"model": "test-model", "usage": {"prompt_tokens": 1}},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(send, contexts))

    for user_id, context in contexts.items():
        assert dialogue.load_chunks(context)[0].payload["content"] == f"hello from {user_id}"
        assert usage.summarize_user("tenant-1", user_id)["total_prompt_tokens"] == 1
        assert not limiter.check(tenant_id="tenant-1", user_id=user_id).allowed
