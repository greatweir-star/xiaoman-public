"""小满后端入口 — FastAPI + WebSocket

改进点：
1. JSONL 持久化 + JSON 快照双写
2. Token Budget 检查
3. Session Compaction 自动压缩
4. 流式输出支持
5. 结构化日志
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.auth.repository import DEFAULT_TENANT_ID
from app.config import get_settings
from app.data_lifecycle.routes import router as data_lifecycle_router
from app.guest_claims.routes import router as guest_claim_router
from app.legacy_security import LegacyApiAuthMiddleware, resolve_ws_auth_user_id
from app.operations.service import get_operational_services
from app.repositories.factory import get_repositories
from app.services.dialogue import DialoguePersistenceService
from app.services.rate_limit import create_rate_limit_service
from app.services.usage import UsageService
from app.services.world_persistence import WorldPersistenceService
from app.security.redaction import configure_redacted_logging
from app.tasks.routes import router as task_router
from app.tasks.service import get_task_service
from app.usage.routes import router as usage_router
from app.ws.context import ConnectionContext
from app.ws.errors import AUTH_FAILED, INVALID_MESSAGE, MODEL_ERROR, RATE_LIMITED, ws_error_payload
from xiaoman.chunk import ChunkKind, ChunkRow, user_text_chunk
from xiaoman.compaction import compact_chunk_table
from xiaoman.llm_service import LLMClient
from xiaoman.loop import run_xiaoman_loop
from xiaoman.emotion import EmotionDetector
from xiaoman.events import WorldEvent, get_event_bus, register_memory_event_handlers
from xiaoman.memory import MemoryEngine
from xiaoman.persistence import (
    SessionWriter,
    load_chat_messages_for_user,
    load_session_from_jsonl,
    load_session_json,
    save_session_json,
)
from xiaoman.dialogue import (
    apply_post_process,
    build_auth_greeting,
    build_strategy_prompt,
    check_phase0_triggers,
    get_school_period,
    parse_user_input,
)
from xiaoman.dialogue.session_context import (
    count_consecutive_low_mood,
    count_user_turns,
    extract_last_topic,
    extract_session_summary,
)
from xiaoman.dialogue.triggers import today_date_str
from xiaoman.dialogue.session_timer import ChatSessionTimer
from xiaoman.daily_avatar import resolve_daily_avatar
from xiaoman.honeymoon import ensure_first_seen, is_honeymoon_active, recall_top_k
from xiaoman import parental as parental_module
from xiaoman.dialogue.boundary import romance_boundary_hints
from xiaoman.dialogue.crisis import check_crisis
from xiaoman import parental
from xiaoman.dialogue.emotion_hold import (
    emotion_hold_strategy_hint,
    finalize_assistant_text,
    needs_emotion_hold,
    pick_emotion_hold_fallback,
)
from xiaoman.dialogue.recall_greeting import build_returning_recall_line
from xiaoman.tools.daily_update import ensure_daily_update
from xiaoman import achievements as achievements_module
from xiaoman import reports as reports_module
from xiaoman.memory.insight_updater import InsightUpdater
from xiaoman.memory.markdown_loader import load_global_memory_snippets
from xiaoman.memory.user_name import build_user_name_prompt_block, extract_name_from_text, is_name_recall_query
from xiaoman.prompts import build_static_prefix, build_dynamic_suffix
from xiaoman.night_mode import build_night_guard_prompt, is_night_hours
from xiaoman.diary_access import annotate_diary_entries
from xiaoman.time_service import TimeService
from xiaoman.world.l1_identity import GRADE_NAMES
from xiaoman.session import XiaomanSession
from xiaoman.tools import (
    MemoryUpdateTool,
    EmotionDetectTool,
    TimeSenseTool,
    NightGuardTool,
    ScheduleRemindTool,
    FocusBuddyTool,
    StudyGuideTool,
)
from xiaoman.world import WorldSystem
from xiaoman.life_timeline import (
    append_event as timeline_append,
    configure_timeline_repository,
    list_events as timeline_list,
    record_period_if_changed,
)
from xiaoman.ws_events import (
    emit_linkage_ws_events,
    format_recall_prompt,
    ws_send_memory_recall,
    ws_send_stream_delta,
    ws_send_stream_end,
    ws_send_stream_start,
    ws_send_typing,
)
from xiaoman.ws_protocol import new_stream_message_id
from xiaoman.achievements import check_achievements, get_achievements_state
from xiaoman.reports import get_latest_weekly_report, get_latest_monthly_report
from xiaoman.life_log import list_logs as life_log_list
from xiaoman.paths import DATA_DIR

# --- 结构化日志 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("xiaoman")
configure_redacted_logging()

app = FastAPI(title="小满后端", version="0.0.1")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LegacyApiAuthMiddleware)
app.include_router(auth_router)
app.include_router(data_lifecycle_router)
app.include_router(guest_claim_router)
app.include_router(task_router)
app.include_router(usage_router)
repositories = get_repositories()
dialogue_persistence = DialoguePersistenceService(repositories) if settings.uses_postgres else None
world_persistence = (
    WorldPersistenceService(repositories.world, tenant_id=DEFAULT_TENANT_ID)
    if settings.uses_postgres
    else None
)
if settings.uses_postgres:
    configure_timeline_repository(repositories.timeline, tenant_id=DEFAULT_TENANT_ID)
usage_service = UsageService(repositories.usage, settings)
rate_limit_service = create_rate_limit_service(settings)
task_service = get_task_service()
operational_services = get_operational_services()

# --- 全局实例 ---
llm_client = LLMClient()
memory_engine = MemoryEngine(llm_client, memory_repository=repositories.memory if settings.uses_postgres else None)
MemoryUpdateTool.bind_engine(memory_engine)
tools = [
    MemoryUpdateTool(),
    EmotionDetectTool(),
    TimeSenseTool(),
    NightGuardTool(),
    ScheduleRemindTool(),
    FocusBuddyTool(),
    StudyGuideTool(),
]
emotion_detector = EmotionDetector(llm_client)
insight_updater = InsightUpdater(llm_client)
time_service = TimeService()
event_bus = get_event_bus()
register_memory_event_handlers(event_bus)

# --- World System 缓存 ---
world_systems: dict[str, WorldSystem] = {}


def get_world(user_id: str) -> WorldSystem:
    """获取或创建用户的世界系统"""
    if user_id not in world_systems:
        user_data_dir = os.path.join(DATA_DIR, "users", user_id)
        if world_persistence:
            try:
                world_persistence.hydrate(user_id=user_id, user_data_dir=user_data_dir)
            except Exception:
                logger.exception("World hydrate failed for user %s", user_id)
        world = WorldSystem(user_id)
        ensure_first_seen(world.user_data_dir)
        world_systems[user_id] = world
        sync_world(world)
    return world_systems[user_id]


def sync_world(world: WorldSystem) -> None:
    if not world_persistence:
        return
    try:
        world_persistence.sync(user_id=world.user_id, user_data_dir=world.user_data_dir)
    except Exception:
        logger.exception("World sync failed for user %s", world.user_id)


ScheduleRemindTool.bind_world(get_world)
FocusBuddyTool.bind_world(get_world)
StudyGuideTool.bind_world(get_world)
memory_engine.set_world_getter(lambda uid: world_systems.get(uid) or get_world(uid))

# --- 数据目录 ---


def load_profile(user_id: str) -> dict[str, Any]:
    path = os.path.join(DATA_DIR, user_id, "profile.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- WebSocket 入口 ---

@app.websocket("/ws")
async def websocket_endpoint_ws(websocket: WebSocket):
    """WebSocket 入口（/ws 路径）"""
    await websocket_endpoint(websocket)

@app.websocket("/")
async def websocket_endpoint_root(websocket: WebSocket):
    """WebSocket 入口（根路径，兼容前端默认连接）"""
    await websocket_endpoint(websocket)

async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 处理逻辑"""
    await websocket.accept()
    user_id = ""
    session = XiaomanSession()
    writer: SessionWriter | None = None
    chat_timer: ChatSessionTimer | None = None
    connection_context: ConnectionContext | None = None

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")
            
            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "payload": {"ts": datetime.now().isoformat()}})
                continue

            if msg_type == "auth":
                try:
                    user_id = resolve_ws_auth_user_id(msg)
                except HTTPException as exc:
                    await websocket.send_json({
                        "type": "auth_error",
                        "payload": ws_error_payload(AUTH_FAILED, str(exc.detail), detail=exc.detail),
                    })
                    await websocket.close(code=4401 if exc.status_code == 401 else 4403)
                    return
                resume = bool(msg.get("resume"))
                session.user_id = user_id
                session.id = user_id or session.id
                chat_timer = ChatSessionTimer()
                if dialogue_persistence:
                    connection_context = dialogue_persistence.open_context(
                        tenant_id=DEFAULT_TENANT_ID,
                        user_id=user_id,
                    )

                # 初始化 WorldSystem
                world = get_world(user_id)
                try:
                    ensure_daily_update(world)
                except Exception:
                    logger.exception("daily_update failed for user %s", user_id)
                try:
                    world.l5_emotion.apply_auth_energy_decay()
                except Exception:
                    logger.exception("auth energy decay failed for user %s", user_id)
                sync_world(world)

                # 初始化 JSONL writer（稳定 user_id 作为 session_id）
                writer = SessionWriter(session.id, user_id)
                writer.write_header()
                
                # PostgreSQL mode restores repository history; file mode keeps the
                # JSON snapshot + JSONL compatibility path during migration.
                if dialogue_persistence and connection_context:
                    repository_rows = dialogue_persistence.load_chunks(connection_context)
                    for row in repository_rows:
                        session.append_chunk(row)
                    logger.info("Loaded %d rows from PostgreSQL for user %s", len(repository_rows), user_id)
                else:
                    history = load_session_json(user_id)
                    jsonl_rows = load_session_from_jsonl(user_id) if not history else []
                    if jsonl_rows:
                        for row in jsonl_rows:
                            session.append_chunk(row)
                        logger.info("Loaded %d rows from JSONL for user %s", len(jsonl_rows), user_id)
                    elif history:
                        for h in history:
                            session.append_chunk(ChunkRow(
                                kind=ChunkKind(h["kind"]),
                                payload=h["payload"],
                            ))
                        logger.info("Loaded %d rows from JSON for user %s", len(history), user_id)

                is_first_session = not session.chunk_table.rows
                ui_messages = (
                    dialogue_persistence.load_ui_messages(connection_context)
                    if dialogue_persistence and connection_context
                    else load_chat_messages_for_user(user_id) if user_id else []
                )
                if ui_messages:
                    await websocket.send_json({
                        "type": "session_sync",
                        "payload": {"messages": ui_messages},
                    })

                returning_recall = ""
                if not is_first_session:
                    last_topic = extract_last_topic(
                        session.chunk_table,
                        fallback="",
                    )
                    session_summary = extract_session_summary(session.chunk_table)
                    memories: list[dict[str, Any]] = []
                    try:
                        memories = memory_engine.recall(
                            user_id, "上次聊天", top_k=2
                        )
                    except Exception:
                        logger.exception("Auth recall failed for user %s", user_id)
                    auth_user = world.l1_identity.get_user()
                    auth_name = memory_engine.resolve_user_display_name(
                        user_id,
                        identity_name=auth_user.get("name", ""),
                        understanding_name=world.l7_profile.get_xiaoman_understanding().get(
                            "name", ""
                        ),
                    )
                    returning_recall = build_returning_recall_line(
                        last_topic=last_topic,
                        session_summary=session_summary,
                        memories=memories,
                        user_name=auth_name,
                    )
                if not resume and is_first_session:
                    greeting, greet_emotion, is_sleeping = build_auth_greeting(
                        world,
                        is_first_session=True,
                        returning_recall="",
                    )
                    identity = world.l1_identity.get_xiaoman()
                    today_state = world.l3_schedule.get_xiaoman().get("xiaoman_today") or {}
                    await websocket.send_json({
                        "type": "message",
                        "payload": {
                            "sender": "xiaoman",
                            "text": greeting,
                            "emotion": greet_emotion,
                            "isSleeping": is_sleeping,
                            "companionCode": identity.get("companion_code"),
                            "todayStatus": today_state.get("mood"),
                        },
                    })
                elif not resume and returning_recall:
                    greeting, greet_emotion, is_sleeping = build_auth_greeting(
                        world,
                        is_first_session=False,
                        returning_recall=returning_recall,
                    )
                    identity = world.l1_identity.get_xiaoman()
                    today_state = world.l3_schedule.get_xiaoman().get("xiaoman_today") or {}
                    await websocket.send_json({
                        "type": "message",
                        "payload": {
                            "sender": "xiaoman",
                            "text": greeting,
                            "emotion": greet_emotion,
                            "isSleeping": is_sleeping,
                            "companionCode": identity.get("companion_code"),
                            "todayStatus": today_state.get("mood"),
                        },
                    })
                continue
            
            if msg_type == "chat":
                user_text = (msg.get("text") or "").strip()
                if not user_text:
                    await websocket.send_json({
                        "type": "error",
                        "payload": ws_error_payload(INVALID_MESSAGE, "消息不能为空"),
                    })
                    continue
                await ws_send_typing(websocket, True)
                try:
                    world = get_world(user_id)
                    user_msg_count = sum(
                        1 for r in session.chunk_table.rows if r.kind == ChunkKind.USER
                    )
                    pcfg = parental.get_config(user_id)
                    crisis = check_crisis(user_text, include_resources=pcfg.crisis_resources_enabled)
                    if crisis.triggered:
                        operational_services.safety.record(
                            tenant_id=DEFAULT_TENANT_ID,
                            user_id=user_id or session.user_id or session.id,
                            category=crisis.category,
                            severity="critical" if crisis.category == "self_harm" else "high",
                            source="websocket_chat",
                            metadata={"resources_included": bool(crisis.resources)},
                        )
                        await websocket.send_json({
                            "type": "message",
                            "payload": {
                                "sender": "xiaoman",
                                "text": crisis.reply,
                                "emotion": "温柔",
                                "crisis": True,
                                "resources": crisis.resources,
                            },
                        })
                        continue

                    rate_limit = rate_limit_service.check(
                        tenant_id=DEFAULT_TENANT_ID,
                        user_id=user_id or session.user_id or session.id,
                    )
                    if not rate_limit.allowed:
                        await websocket.send_json({
                            "type": "error",
                            "payload": ws_error_payload(
                                RATE_LIMITED,
                                "消息有点密啦，稍等一下再和我说吧～",
                                **{"retryAfterSeconds": rate_limit.retry_after_seconds},
                            ),
                        })
                        continue

                    parsed = parse_user_input(user_text)
                    rest_round_warn = False
                    session_time_warn = False
                    elapsed_min = 0.0
                    if chat_timer:
                        rest_round_warn = chat_timer.check_rest_round(user_msg_count)
                        session_time_warn = chat_timer.check_session_time()
                        elapsed_min = chat_timer.elapsed_minutes()
                    phase0 = check_phase0_triggers(
                        user_message=user_text,
                        message_count=user_msg_count,
                        user_emotion=parsed.emotion,
                        session_elapsed_minutes=elapsed_min,
                        rest_round_warn=rest_round_warn,
                        session_time_warn=session_time_warn,
                    )
                    if phase0.blocked:
                        await websocket.send_json({
                            "type": "message",
                            "payload": {
                                "sender": "xiaoman",
                                "text": phase0.block_reply,
                                "emotion": phase0.block_emotion,
                                "isSleeping": phase0.is_sleeping,
                            },
                        })
                        continue

                    user_chunk = user_text_chunk(user_text)
                    session.append_chunk(user_chunk)
                    if writer:
                        writer.write_chunk(user_chunk)
                    if dialogue_persistence and connection_context:
                        dialogue_persistence.append_chunk(connection_context, user_chunk)

                    if len(session.chunk_table.rows) > 12:
                        logger.info("Session compaction triggered for user %s", user_id)
                        session.chunk_table = compact_chunk_table(
                            session.chunk_table, llm_client, max_messages=12, keep_recent=4
                        )

                    identity = world.l1_identity.get_user()
                    gender = identity.get("gender", "female")
                    user_grade = identity.get("grade", "")
                    effective_user_id = user_id or session.user_id or session.id
                    understanding = world.l7_profile.get_xiaoman_understanding()
                    user_name = memory_engine.resolve_user_display_name(
                        effective_user_id,
                        identity_name=identity.get("name", ""),
                        understanding_name=understanding.get("name", ""),
                    )
                    name_query = is_name_recall_query(user_text)
                    life_context = world.get_life_context_for_prompt()
                    dialogue_context = world.get_dialogue_context_for_prompt()
                    user_context = world.get_user_context()
                    skill_tree = world.get_skill_tree()
                    period = get_school_period()

                    if not world.get_diary(today_date_str()):
                        try:
                            activity = world.l3_schedule.get_xiaoman().get(
                                "current_activity", "平常的一天"
                            )
                            diary_text = f"今天：{activity}"
                            world.l8_dialogue.add_diary_entry(
                                today_date_str(),
                                diary_text,
                            )
                            timeline_append(
                                effective_user_id,
                                "diary",
                                "写了今日日记",
                                detail=diary_text,
                                meta={"date": today_date_str()},
                            )
                        except Exception:
                            logger.exception("Daily log bootstrap failed for user %s", user_id)

                    try:
                        record_period_if_changed(effective_user_id, period.period)
                    except Exception:
                        logger.exception("Period timeline failed for user %s", user_id)

                    event_bus.publish(WorldEvent(
                        type="user_input",
                        user_id=effective_user_id,
                        payload={"text": user_text, "session_id": session.id},
                    ))

                    detected = emotion_detector.detect(user_text)
                    u_em = world.l5_emotion._load(world.l5_emotion.u_path)
                    u_em["current_emotion"] = detected.emotion
                    world.l5_emotion._save(world.l5_emotion.u_path, u_em)
                    event_bus.publish(WorldEvent(
                        type="emotion_detected",
                        user_id=effective_user_id,
                        payload={
                            "emotion": detected.emotion,
                            "confidence": detected.confidence,
                            "source": detected.source,
                            "text_preview": user_text[:80],
                        },
                    ))

                    pre_changes = world.l5_emotion.detect_user_emotion(user_text)
                    pre_linkage = world.linkage.evaluate(user_text, pre_changes)
                    await emit_linkage_ws_events(websocket, pre_linkage)
                    for change in pre_linkage:
                        label = change.get("result") or change.get("linkage") or "联动"
                        try:
                            timeline_append(
                                effective_user_id,
                                "linkage",
                                str(label),
                                meta={"linkage": change.get("linkage")},
                            )
                        except Exception:
                            pass
                    linkage_hints = world.get_linkage_prompt_hints()
                    romance_hints = romance_boundary_hints(user_text, gender)

                    recall_k = recall_top_k(world.user_data_dir, default=3)
                    recalled = memory_engine.recall(
                        effective_user_id, user_text, top_k=recall_k
                    )
                    await ws_send_memory_recall(websocket, recalled)
                    name_block = build_user_name_prompt_block(
                        user_name, is_name_query=name_query
                    )
                    memory_context = name_block + format_recall_prompt(recalled)

                    message_count = count_user_turns(session.chunk_table)
                    session_summary = extract_session_summary(session.chunk_table)
                    last_topic = extract_last_topic(session.chunk_table)
                    low_mood_streak = count_consecutive_low_mood(session.chunk_table)
                    extra_hints = list(phase0.strategy_hints) + romance_hints
                    if needs_emotion_hold(parsed, detected_emotion=detected.emotion):
                        extra_hints.append(emotion_hold_strategy_hint(gender))
                    if is_honeymoon_active(world.user_data_dir):
                        extra_hints.append(
                            "【蜜月期】用户刚认识不久，多主动引用已记住的细节，让 TA 感到被懂得。"
                        )
                    strategy_block = build_strategy_prompt(
                        parsed,
                        period,
                        gender,
                        last_topic=last_topic,
                        consecutive_low_mood=low_mood_streak,
                        extra_hints=extra_hints,
                    )

                    static_prefix = build_static_prefix(gender)
                    time_alerts = world.time_service.check_special_dates(
                        world.l3_schedule.get_user()
                    )
                    prompt_user_ctx = dict(user_context)
                    prompt_user_ctx["social"] = world.get_xiaoman_context().get("social", {})
                    dynamic_suffix = build_dynamic_suffix(
                        user_name=user_name,
                        user_grade=user_grade,
                        message_count=message_count,
                        summary=session_summary,
                        last_chat_time=session.updated_at.strftime("%Y-%m-%d %H:%M"),
                        life_context=life_context,
                        dialogue_context=dialogue_context,
                        user_context=prompt_user_ctx,
                        skill_tree=skill_tree,
                        revealed_social=world.get_revealed_social_prompt(),
                        time_alerts=time_alerts,
                        global_memory=load_global_memory_snippets(),
                    )
                    night_block = ""
                    if is_night_hours():
                        night_block = build_night_guard_prompt() + "\n\n"
                    system_prompt = (
                        f"{static_prefix}\n\n{strategy_block}\n\n"
                        f"{night_block}{linkage_hints}{memory_context}{dynamic_suffix}"
                    )

                    loop_failed = False
                    use_stream = msg.get("stream", True)
                    stream_message_id = new_stream_message_id()
                    if use_stream:
                        await ws_send_stream_start(websocket, stream_message_id)
                    event_loop = asyncio.get_running_loop()

                    def on_stream_delta(text: str) -> None:
                        asyncio.run_coroutine_threadsafe(
                            ws_send_stream_delta(websocket, stream_message_id, text),
                            event_loop,
                        )

                    def on_llm_usage(event: dict[str, Any]) -> None:
                        usage_service.record_llm_call(
                            tenant_id=connection_context.tenant_id if connection_context else DEFAULT_TENANT_ID,
                            user_id=user_id or session.user_id or session.id,
                            session_id=connection_context.session_id if connection_context else session.id,
                            event=event,
                        )

                    try:
                        session = await asyncio.to_thread(
                            run_xiaoman_loop,
                            session=session,
                            system_prompt=system_prompt,
                            tools=tools,
                            llm_client=llm_client,
                            max_tool_rounds=4,
                            on_stream_delta=on_stream_delta if use_stream else None,
                            on_usage=on_llm_usage,
                        )
                    except Exception as e:
                        loop_failed = True
                        logger.exception("Session loop failed for user %s", user_id)
                        await websocket.send_json({
                            "type": "error",
                            "payload": ws_error_payload(MODEL_ERROR, "回复暂时生成失败，请稍后再试"),
                        })
                        if needs_emotion_hold(parsed, detected_emotion=detected.emotion):
                            err_text = pick_emotion_hold_fallback(
                                user_text,
                                parsed,
                                user_gender=gender,
                                user_name=user_name,
                                detected_emotion=detected.emotion,
                            )
                        else:
                            err_text = f"我这边出错了: {str(e)}"
                        if use_stream:
                            await ws_send_stream_end(
                                websocket,
                                stream_message_id,
                                text=err_text,
                                emotion="温柔",
                            )
                        else:
                            await websocket.send_json({
                                "type": "message",
                                "payload": {
                                    "sender": "xiaoman",
                                    "text": err_text,
                                    "emotion": "温柔",
                                },
                            })

                    if not loop_failed and session.budget_exceeded:
                        logger.warning(
                            "Budget exceeded for user %s: %d tokens",
                            user_id,
                            session.cumulative_usage,
                        )
                        budget_text = "今天聊了好多啦，休息一下明天再继续吧~"
                        if use_stream:
                            await ws_send_stream_end(
                                websocket,
                                stream_message_id,
                                text=budget_text,
                                emotion="温柔",
                            )
                        else:
                            await websocket.send_json({
                                "type": "message",
                                "payload": {
                                    "sender": "xiaoman",
                                    "text": budget_text,
                                    "emotion": "温柔",
                                },
                            })
                    elif not loop_failed:
                        last_assistant = None
                        for row in reversed(session.chunk_table.rows):
                            if row.kind == ChunkKind.ASSISTANT:
                                last_assistant = row
                                break

                        if last_assistant:
                            text = last_assistant.payload.get("content", "")
                            emotion = llm_client.extract_emotion(text)
                            clean_text = llm_client.clean_emotion_tags(text)

                            clean_text, used_hold_fallback = finalize_assistant_text(
                                clean_text,
                                user_text,
                                parsed,
                                user_gender=gender,
                                user_name=user_name,
                                detected_emotion=detected.emotion,
                            )
                            if used_hold_fallback:
                                emotion = "温柔"

                            processed = apply_post_process(
                                clean_text,
                                period=period,
                                parsed=parsed,
                                inject_guess_mood=phase0.inject_guess_mood,
                                guess_mood_text=phase0.guess_mood_text,
                            )
                            clean_text = processed.text

                            if writer:
                                writer.write_chunk(last_assistant)
                            if dialogue_persistence and connection_context:
                                dialogue_persistence.append_message(
                                    connection_context,
                                    role=ChunkKind.ASSISTANT.value,
                                    content=clean_text,
                                    metadata={"emotion": emotion},
                                )

                            try:
                                linkage_changes = world.update_from_message(user_text, clean_text)
                                insight_updater.update_after_turn(
                                    world,
                                    user_text=user_text,
                                    assistant_text=clean_text,
                                    detected_emotion=detected.emotion,
                                    message_count=message_count,
                                )
                                sync_world(world)
                                xp_result = world.l6_skills.add_xp(1)
                                if xp_result.get("new_level", 1) > xp_result.get("old_level", 1):
                                    await websocket.send_json({
                                        "type": "skill_unlocked",
                                        "payload": xp_result,
                                    })
                                if linkage_changes:
                                    logger.info(
                                        "Linkage changes for user %s: %s",
                                        effective_user_id,
                                        linkage_changes,
                                    )
                                    event_bus.publish(WorldEvent(
                                        type="linkage_triggered",
                                        user_id=effective_user_id,
                                        payload={"changes": linkage_changes},
                                    ))
                                    await emit_linkage_ws_events(websocket, linkage_changes)
                                    for change in linkage_changes:
                                        label = change.get("result") or change.get("linkage") or "联动"
                                        try:
                                            timeline_append(
                                                effective_user_id,
                                                "linkage",
                                                str(label),
                                                meta={"linkage": change.get("linkage")},
                                            )
                                        except Exception:
                                            pass
                            except Exception as e:
                                logger.exception("WorldSystem update failed for user %s", user_id)

                            session.xiaoman_mood = emotion
                            xm_emotion = world.l5_emotion.get_xiaoman()
                            session.xiaoman_energy = xm_emotion.get("energy", 50)

                            is_sleeping = get_school_period().period == "sleep"
                            try:
                                preview = user_text.replace("\n", " ")[:40]
                                timeline_append(
                                    effective_user_id,
                                    "chat",
                                    f"聊天 · {preview}",
                                    detail=clean_text[:160],
                                    meta={"emotion": emotion},
                                )
                            except Exception:
                                logger.exception("Chat timeline failed for user %s", user_id)

                            xm_energy = int(xm_emotion.get("energy", 50))
                            if use_stream:
                                await ws_send_stream_end(
                                    websocket,
                                    stream_message_id,
                                    text=clean_text,
                                    emotion=emotion,
                                    is_sleeping=is_sleeping,
                                    energy=xm_energy,
                                )
                            else:
                                await websocket.send_json({
                                    "type": "message",
                                    "payload": {
                                        "sender": "xiaoman",
                                        "text": clean_text,
                                        "emotion": emotion,
                                        "isSleeping": is_sleeping,
                                        "energy": xm_energy,
                                    },
                                })
                            if phase0.rest_reminder:
                                await websocket.send_json({
                                    "type": "rest_reminder",
                                    "payload": {
                                        "reason": "rounds",
                                        "message": "你已经聊了很多轮啦，眼睛累不累？休息一下～",
                                    },
                                })
                            if phase0.session_time_warning:
                                await websocket.send_json({
                                    "type": "rest_reminder",
                                    "payload": {
                                        "reason": "session_time",
                                        "message": "我们聊了好久啦，起来活动一下、看看远处吧～",
                                    },
                                })

                        if settings.uses_queue:
                            task_service.enqueue(
                                tenant_id=connection_context.tenant_id if connection_context else DEFAULT_TENANT_ID,
                                user_id=user_id or session.user_id or session.id,
                                task_type="memory_extract",
                                payload={
                                    "session_id": session.id,
                                    "messages": session.chunk_table.to_llm_messages(),
                                },
                            )
                        else:
                            memory_engine.extract(session)
                        save_session_json(session)
                finally:
                    await ws_send_typing(websocket, False)
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", user_id)
    except Exception as e:
        logger.exception("WebSocket error for user %s", user_id)
        try:
            await websocket.send_json({
                "type": "message",
                "payload": {
                    "sender": "xiaoman",
                    "text": f"我这边出错了: {str(e)}",
                    "emotion": "温柔",
                },
            })
        except Exception:
            pass
    finally:
        if writer:
            writer.write_trailer()


# --- Dreaming 定时任务 ---

def dreaming_scheduler():
    """每晚 23:00 执行 Dreaming"""
    while True:
        now = datetime.now()
        # 计算到下一个 23:00 的秒数
        target = now.replace(hour=23, minute=0, second=0, microsecond=0)
        if now >= target:
            target = target.replace(day=target.day + 1)
        sleep_seconds = (target - now).total_seconds()
        
        logger.info("Dreaming scheduler sleeping for %.0f seconds until %s", sleep_seconds, target)
        time.sleep(sleep_seconds)
        
        try:
            user_ids = memory_engine.store.list_user_ids_with_memory()
            users_dir = os.path.join(DATA_DIR, "users")
            if os.path.exists(users_dir):
                for name in os.listdir(users_dir):
                    if name not in user_ids:
                        user_ids.append(name)
            for uid in user_ids:
                if not uid:
                    continue
                if settings.uses_queue:
                    logger.info("Queueing nightly flow for user %s", uid)
                    task_service.enqueue(
                        tenant_id=DEFAULT_TENANT_ID,
                        user_id=uid,
                        task_type="dreaming",
                        payload={},
                    )
                else:
                    logger.info("Running nightly flow for user %s", uid)
                    memory_engine.run_nightly_flow(uid, world=get_world(uid))
                try:
                    timeline_append(uid, "dreaming", "夜间记忆整理", detail="Light → Promote → Cleanup")
                except Exception:
                    logger.exception("Dreaming timeline failed for user %s", uid)
        except Exception as e:
            logger.exception("Dreaming scheduler error: %s", e)

# --- REST API 端点 ---

from fastapi import Query

@app.get("/api/world/{user_id}")
async def get_world_state(user_id: str):
    """获取用户完整世界状态"""
    world = get_world(user_id)
    return world.to_dict()

@app.get("/api/world/{user_id}/xiaoman")
async def get_xiaoman_state(user_id: str):
    """获取小满状态"""
    world = get_world(user_id)
    try:
        ensure_daily_update(world)
    except Exception:
        logger.exception("daily_update failed for user %s", user_id)
    ctx = world.get_xiaoman_context()
    ctx["companion_code"] = world.l1_identity.get_companion_code()
    return ctx

@app.get("/api/world/{user_id}/growth")
async def get_growth_timeline(user_id: str):
    """成长时间轴 — 小满眼中的成长节点 + 情绪天气"""
    world = get_world(user_id)
    understanding = world.l7_profile.get_xiaoman_understanding()
    return {
        "emotional_weather": world.l7_profile.get_emotional_weather(),
        "emotion_patterns": understanding.get("emotion_patterns", []),
        "growth_moments": world.l7_profile.list_growth_moments(),
    }


@app.get("/api/world/{user_id}/skill-tree")
async def get_skill_tree(user_id: str):
    """获取技能树"""
    world = get_world(user_id)
    return world.get_skill_tree()


@app.get("/api/world/{user_id}/achievements")
async def get_achievements(user_id: str):
    """获取全部成就状态"""
    return get_achievements_state(user_id)


@app.post("/api/world/{user_id}/achievements/check")
async def post_check_achievements(user_id: str):
    """触发成就检查，返回新增解锁"""
    if settings.uses_queue:
        task = task_service.enqueue(
            tenant_id=DEFAULT_TENANT_ID,
            user_id=user_id,
            task_type="achievement_check",
            payload={},
        )
        return {"status": "queued", "task_id": task["id"]}
    newly = check_achievements(user_id)
    return {"newly_unlocked": newly, "total_unlocked": len(get_achievements_state(user_id).get("achievements", []))}


@app.get("/api/world/{user_id}/reports/weekly")
async def get_weekly_report(user_id: str):
    """获取最新周报告（不存在则懒生成）"""
    return get_latest_weekly_report(user_id)


@app.get("/api/world/{user_id}/reports/monthly")
async def get_monthly_report(user_id: str):
    """获取最新月报告（不存在则懒生成）"""
    return get_latest_monthly_report(user_id)


@app.post("/api/world/{user_id}/reports/{period}/generate")
async def generate_report(user_id: str, period: str):
    """Generate a report inline or enqueue it for the worker."""
    if period not in {"weekly", "monthly"}:
        raise HTTPException(status_code=422, detail="period must be weekly or monthly")
    task_type = f"{period}_report"
    if settings.uses_queue:
        task = task_service.enqueue(
            tenant_id=DEFAULT_TENANT_ID,
            user_id=user_id,
            task_type=task_type,
            payload={},
        )
        return {"status": "queued", "task_id": task["id"]}
    if period == "weekly":
        return reports_module.generate_weekly_report(user_id, force=True)
    return reports_module.generate_monthly_report(user_id, force=True)


@app.get("/api/world/{user_id}/daily-avatar")
async def get_daily_avatar(user_id: str, style: str = Query(None)):
    """每日形象 MVP — 静态轮换 + 可选生图 hook"""
    world = get_world(user_id)
    identity = world.l1_identity.get_user()
    style = style or identity.get("art_style") or identity.get("style") or "fresh"
    from xiaoman.image_generation import resolve_image_hook

    hook = resolve_image_hook()
    image_url = hook if hook.startswith("http") else None
    return resolve_daily_avatar(
        style=style,
        image_api_url=image_url,
        user_id=user_id,
    )


@app.get("/api/profile/{user_id}")
async def get_profile_api(user_id: str):
    """用户画像（PRD memory-03 §9.1 别名）"""
    world = get_world(user_id)
    return world.get_user_context()


@app.get("/api/skill-tree/{user_id}")
async def get_skill_tree_api(user_id: str):
    """技能树（PRD memory-03 §9.1 别名）"""
    return await get_skill_tree(user_id)

@app.get("/api/world/{user_id}/timeline")
async def get_life_timeline(user_id: str, limit: int = Query(80, ge=1, le=200)):
    """小满生活时间线（按时间倒序）"""
    return {"entries": timeline_list(user_id, limit=limit)}


@app.get("/api/world/{user_id}/life-log")
async def get_life_log(user_id: str, limit: int = Query(50, ge=1, le=200)):
    """小满生活日志 JSONL（结构化事件流水）"""
    return {"entries": life_log_list(user_id, limit=limit)}


@app.get("/api/world/{user_id}/diary")
async def get_diary(user_id: str, date: str = Query(None)):
    """获取日记（含关系等级锁定标注）"""
    world = get_world(user_id)
    entries = world.get_diary(date)
    level = world.get_relation_level()
    return {"entries": annotate_diary_entries(entries, relation_level=level), "relation_level": level}

@app.get("/api/world/{user_id}/social")
async def get_social_graph(user_id: str, side: str = Query("xiaoman")):
    """获取社交关系图"""
    world = get_world(user_id)
    return world.get_social_graph(side)

@app.get("/api/memory/{user_id}")
async def get_memory(user_id: str, query: str = "", top_k: int = 5):
    """记忆语义检索"""
    if query:
        return {"memories": memory_engine.recall(user_id, query, top_k=top_k)}
    return {
        "facts": memory_engine.get_facts(user_id),
        "organized": memory_engine.get_organized(user_id),
        "long_term": memory_engine.get_long_term_memories(user_id),
    }


@app.post("/api/memory/{user_id}")
async def update_memory(user_id: str, data: dict):
    """手动写入记忆"""
    fact = data.get("fact") or data.get("content", "")
    if not fact:
        return {"status": "error", "message": "fact required"}
    category = data.get("category", "general")
    layer = data.get("layer", "L7")
    if extract_name_from_text(fact):
        category = "identity"
        layer = "L1"
    saved = memory_engine.save_fact(user_id, fact, category, layer)
    if saved:
        world = get_world(user_id)
        from xiaoman.world.fact_router import apply_facts_to_world
        apply_facts_to_world(world, [{"content": fact, "category": category, "layer": layer}])
        sync_world(world)
    return {"status": "ok", "fact": fact, "deduplicated": not saved}


@app.get("/api/memory/{user_id}/stats")
async def memory_stats(user_id: str):
    return memory_engine.stats(user_id)


@app.get("/api/memory/{user_id}/diary")
async def memory_diary(user_id: str, date: str = Query(None)):
    world = get_world(user_id)
    entries = memory_engine.get_diary(user_id, date)
    level = world.get_relation_level()
    return {
        "entries": annotate_diary_entries(entries, relation_level=level),
        "relation_level": level,
    }


@app.post("/api/memory/{user_id}/dreaming")
async def trigger_dreaming(user_id: str):
    """手动触发夜间整理（Light → Promote → Cleanup → REM）"""
    if settings.uses_queue:
        task = task_service.enqueue(
            tenant_id=DEFAULT_TENANT_ID,
            user_id=user_id,
            task_type="dreaming",
            payload={},
        )
        return {"status": "queued", "task_id": task["id"]}
    result = memory_engine.run_nightly_flow(user_id, world=get_world(user_id))
    return {"status": "ok", **result}


@app.get("/api/memory/{user_id}/secrets")
async def list_secrets(user_id: str, reveal: bool = Query(False)):
    world = get_world(user_id)
    return {"secrets": world.l7_profile.list_secrets(reveal=reveal)}


@app.get("/api/memory/{user_id}/lineage/{node_id}")
async def get_memory_lineage(user_id: str, node_id: str):
    """记忆血缘溯源"""
    trace = memory_engine.trace_lineage(user_id, node_id)
    summary = memory_engine.get_lineage_summary(user_id, node_id)
    return {
        "node_id": node_id,
        "summary": summary,
        "trace": [
            {
                "id": getattr(n, "id", ""),
                "content": getattr(n, "content", ""),
                "node_type": getattr(n, "node_type", ""),
            }
            for n in trace
        ],
    }


def _resolve_grade(value: int | str) -> int | None:
    if isinstance(value, int):
        return value if 7 <= value <= 12 else None
    if isinstance(value, str):
        for num, name in GRADE_NAMES.items():
            if value == name or value == str(num):
                return num
    return None


@app.post("/api/world/{user_id}/identity")
async def update_identity(user_id: str, data: dict):
    """更新用户/小满身份（Onboarding 同步）"""
    world = get_world(user_id)
    companion = data.get("companion_name") or data.get("xiaoman_name")
    if companion:
        world.l1_identity.set_xiaoman_name(companion)
    if "name" in data:
        world.l1_identity.set_user_name(data["name"])
    if "grade" in data:
        grade_num = _resolve_grade(data["grade"])
        if grade_num is not None:
            world.l1_identity.set_user_grade(grade_num)
    if "gender" in data:
        world.l1_identity.set_user_gender(data["gender"])
    if "style" in data or "art_style" in data:
        world.l1_identity.set_user_art_style(data.get("style") or data.get("art_style"))
    if "school" in data:
        world.l1_identity.set_user_school(data["school"], data.get("class", ""))
    ensure_first_seen(world.user_data_dir)
    sync_world(world)
    return {
        "status": "ok",
        "honeymoon_active": is_honeymoon_active(world.user_data_dir),
    }

# Dreaming scheduler is optional. Keep it off by default for local development,
# tests, and short-lived containers; enable with XIAOMAN_ENABLE_DREAMING_SCHEDULER=true.
def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if _env_flag("XIAOMAN_ENABLE_DREAMING_SCHEDULER", default=False):
    dreaming_thread = threading.Thread(target=dreaming_scheduler, daemon=True)
    dreaming_thread.start()
    logger.info("Dreaming scheduler enabled")
else:
    logger.info("Dreaming scheduler disabled")


# === V0.03 parental routes ===
@app.get("/api/world/{user_id}/parental")
async def get_parental_config(user_id: str):
    config = parental_module.get_config(user_id)
    return config.dict()

@app.post("/api/world/{user_id}/parental")
async def update_parental_config(user_id: str, body: dict):
    ok = parental_module.update_config(
        user_id, body.get("config", {}), body.get("password", "")
    )
    return {"success": ok}

@app.get("/api/world/{user_id}/usage")
async def get_usage(user_id: str):
    limits = parental_module.check_usage_limits(user_id)
    return limits


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18789)
