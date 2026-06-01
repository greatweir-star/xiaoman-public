from app.repositories.file import create_file_repositories
from app.services.dialogue import DialoguePersistenceService
from xiaoman.chunk import ChunkKind, assistant_turn_chunk, user_text_chunk


def test_dialogue_persistence_roundtrip(tmp_path):
    service = DialoguePersistenceService(create_file_repositories(str(tmp_path)))
    context = service.open_context(tenant_id="tenant-1", user_id="user-1")

    service.append_chunk(context, user_text_chunk("hello"))
    service.append_chunk(context, assistant_turn_chunk("hi"))

    chunks = service.load_chunks(context)
    assert [(chunk.kind, chunk.payload["content"]) for chunk in chunks] == [
        (ChunkKind.USER, "hello"),
        (ChunkKind.ASSISTANT, "hi"),
    ]
    assert service.load_ui_messages(context) == [
        {"sender": "user", "text": "hello", "kind": "normal"},
        {"sender": "xiaoman", "text": "hi", "kind": "normal"},
    ]


def test_dialogue_persistence_ignores_non_chat_chunks(tmp_path):
    service = DialoguePersistenceService(create_file_repositories(str(tmp_path)))
    context = service.open_context(tenant_id="tenant-1", user_id="user-1")

    service.append_chunk(context, user_text_chunk("hello"))
    service.append_message(context, role="tool_result", content="internal")

    assert service.load_ui_messages(context) == [
        {"sender": "user", "text": "hello", "kind": "normal"},
    ]


def test_dialogue_persistence_restores_file_metadata(tmp_path):
    service = DialoguePersistenceService(create_file_repositories(str(tmp_path)))
    context = service.open_context(tenant_id="tenant-1", user_id="user-1")

    service.append_message(context, role="assistant", content="hi", metadata={"emotion": "温柔"})

    assert service.load_chunks(context)[0].payload == {"content": "hi", "emotion": "温柔"}
