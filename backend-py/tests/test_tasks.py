from app.tasks.repository import InMemoryTaskRepository
from app.tasks.service import TaskService


def test_task_service_executes_and_completes_task():
    repository = InMemoryTaskRepository()
    service = TaskService(repository)
    queued = service.enqueue(
        tenant_id="tenant-1",
        user_id="user-1",
        task_type="echo",
        payload={"value": 7},
    )

    completed = service.run_once(
        worker_id="worker-1",
        handlers={"echo": lambda task: {"value": task["payload"]["value"]}},
    )

    assert completed["id"] == queued["id"]
    assert completed["status"] == "completed"
    assert service.list_for_user("tenant-1", "user-1")[0]["result"] == {"value": 7}


def test_task_service_retries_then_marks_task_failed():
    repository = InMemoryTaskRepository()
    service = TaskService(repository, retry_delay_seconds=0)
    service.enqueue(
        tenant_id="tenant-1",
        user_id="user-1",
        task_type="fail",
        payload={},
        max_attempts=2,
    )

    def fail(_task):
        raise RuntimeError("try again")

    service.run_once(worker_id="worker-1", handlers={"fail": fail})
    first = service.list_for_user("tenant-1", "user-1")[0]
    assert first["status"] == "pending"
    assert first["attempt_count"] == 1

    service.run_once(worker_id="worker-1", handlers={"fail": fail})
    second = service.list_for_user("tenant-1", "user-1")[0]
    assert second["status"] == "failed"
    assert second["attempt_count"] == 2
    assert second["error_message"] == "try again"


def test_task_list_is_scoped_to_user():
    service = TaskService(InMemoryTaskRepository())
    service.enqueue(tenant_id="tenant-1", user_id="user-a", task_type="echo", payload={})
    service.enqueue(tenant_id="tenant-1", user_id="user-b", task_type="echo", payload={})

    rows = service.list_for_user("tenant-1", "user-a")

    assert len(rows) == 1
    assert rows[0]["user_id"] == "user-a"
