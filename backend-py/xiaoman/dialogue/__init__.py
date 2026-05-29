"""对话生成流水线 — 对照《小满对话生成逻辑方案》Phase 0–5"""

from xiaoman.dialogue.greeting import build_auth_greeting
from xiaoman.dialogue.input_parser import ParsedInput, parse_user_input
from xiaoman.dialogue.period import PeriodInfo, get_school_period, is_night_sleep_period
from xiaoman.dialogue.post_process import PostProcessResult, apply_post_process
from xiaoman.dialogue.strategy import build_strategy_prompt
from xiaoman.dialogue.triggers import Phase0Result, check_phase0_triggers

__all__ = [
    "build_auth_greeting",
    "ParsedInput",
    "parse_user_input",
    "PeriodInfo",
    "get_school_period",
    "is_night_sleep_period",
    "PostProcessResult",
    "apply_post_process",
    "build_strategy_prompt",
    "Phase0Result",
    "check_phase0_triggers",
]
