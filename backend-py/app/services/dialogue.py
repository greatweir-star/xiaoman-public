"""Repository-backed persistence helpers for the dialogue WebSocket."""

from __future__ import annotations

from typing import Any

from app.repositories import RepositoryBundle
from app.ws.context import ConnectionContext
from xiaoman.chunk import ChunkKind, ChunkRow


class DialoguePersistenceService:
    def __init__(self, repositories: RepositoryBundle) -> None:
        self.repositories = repositories

    def open_context(self, *, tenant_id: str, user_id: str, companion_id: str = "xiaoman") -> ConnectionContext:
        session_id = self.repositories.sessions.get_or_create_session(tenant_id, user_id, companion_id)
        return ConnectionContext(
            tenant_id=tenant_id,
            user_id=user_id,
            companion_id=companion_id,
            session_id=session_id,
        )

    def append_chunk(self, context: ConnectionContext, chunk: ChunkRow) -> None:
        if chunk.kind not in {ChunkKind.USER, ChunkKind.ASSISTANT}:
            return
        self.append_message(
            context,
            role=chunk.kind.value,
            content=str(chunk.payload.get("content") or ""),
            metadata={key: value for key, value in chunk.payload.items() if key != "content"},
        )

    def append_message(
        self,
        context: ConnectionContext,
        *,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.repositories.sessions.append_message(
            context.session_id,
            {"role": role, "content": content, **(metadata or {})},
        )

    def load_chunks(self, context: ConnectionContext) -> list[ChunkRow]:
        chunks: list[ChunkRow] = []
        for message in self.repositories.sessions.load_messages(context.session_id):
            role = str(message.get("role") or "")
            if role not in {ChunkKind.USER.value, ChunkKind.ASSISTANT.value}:
                continue
            metadata = dict(message.get("metadata") or {})
            metadata.update(
                {
                    key: value
                    for key, value in message.items()
                    if key not in {"id", "type", "role", "content", "metadata", "created_at"}
                }
            )
            chunks.append(ChunkRow(kind=ChunkKind(role), payload={"content": message.get("content") or "", **metadata}))
        return chunks

    def load_ui_messages(self, context: ConnectionContext) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for chunk in self.load_chunks(context):
            text = str(chunk.payload.get("content") or "").strip()
            if text:
                messages.append(
                    {
                        "sender": "user" if chunk.kind == ChunkKind.USER else "xiaoman",
                        "text": text,
                        "kind": "normal",
                    }
                )
        return messages
