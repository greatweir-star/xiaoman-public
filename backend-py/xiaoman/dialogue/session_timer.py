"""WebSocket 会话计时 — 30 分钟防沉迷提醒"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from xiaoman.dialogue.config import anti_addiction_config


@dataclass
class ChatSessionTimer:
    """单次 WS 连接内的活跃聊天计时（monotonic）。"""

    started_at: float = field(default_factory=time.monotonic)
    rest_round_warned: bool = False
    session_time_warned: bool = False

    def elapsed_minutes(self) -> float:
        return (time.monotonic() - self.started_at) / 60.0

    def check_rest_round(self, message_count: int) -> bool:
        """第 N 轮（已完成轮数）触发一次休息提醒。"""
        cfg = anti_addiction_config()
        if not cfg["enabled"]:
            return False
        threshold = cfg["warn_rounds"]
        if self.rest_round_warned or message_count < threshold:
            return False
        self.rest_round_warned = True
        return True

    def check_session_time(self) -> bool:
        """连续在线达 warn_minutes 后触发一次。"""
        cfg = anti_addiction_config()
        if not cfg["enabled"]:
            return False
        if self.session_time_warned:
            return False
        if self.elapsed_minutes() < cfg["warn_minutes"]:
            return False
        self.session_time_warned = True
        return True
