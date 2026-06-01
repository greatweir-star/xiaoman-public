from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.repository import AuthUser
from app.dependencies import get_current_user
from app.tasks.repository import InMemoryTaskRepository
from app.tasks.routes import router
from app.tasks.service import TaskService, get_task_service


def test_my_tasks_route_is_authenticated_and_scoped():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    assert client.get("/api/tasks/me").status_code == 401

    service = TaskService(InMemoryTaskRepository())
    service.enqueue(tenant_id="tenant-1", user_id="user-1", task_type="echo", payload={})

    async def current_user():
        return AuthUser(
            id="user-1",
            tenant_id="tenant-1",
            email="tasks@example.com",
            password_hash="unused",
        )

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_task_service] = lambda: service

    response = client.get("/api/tasks/me")
    assert response.status_code == 200
    assert response.json()["tasks"][0]["task_type"] == "echo"
