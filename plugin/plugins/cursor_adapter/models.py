"""Cursor Adapter — 数据模型。

定义适配器运行所需的配置、会话、执行结果等数据结构。
所有结构都是纯 dataclass，不依赖 SDK 内部类型，
方便单元测试和未来扩展。

字段含义与 Paperclip `cursor-local` 适配器对齐，
并补充 N.E.K.O 插件所需的额外选项。

与 Codex 适配器的关键差异：
- 会话 ID 字段为 ``session_id``（而非 ``thread_id``）
- 有 ``mode`` 执行模式（agent/build/ask/browse），而非 ``model_reasoning_effort``
- 绕过审批用 ``--yolo``（而非 ``--dangerously-bypass-approvals-and-sandbox``）
- 有 ``cost_usd`` 成本追踪（Cursor stream-json 的 result 事件携带 total_cost_usd）
- 无 CODEX_HOME / openai_api_key 概念
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal


# ---------------------------------------------------------------------------
# 适配器配置
# ---------------------------------------------------------------------------


# Cursor Agent CLI 已知模型列表（来自 paperclip cursor-local/src/index.ts）
CURSOR_KNOWN_MODELS: tuple[str, ...] = (
    "auto",
    "composer-1.5",
    "composer-1",
    "gpt-5.3-codex-low",
    "gpt-5.3-codex-low-fast",
    "gpt-5.3-codex",
    "gpt-5.3-codex-fast",
    "gpt-5.3-codex-high",
    "gpt-5.3-codex-high-fast",
    "gpt-5.3-codex-xhigh",
    "gpt-5.3-codex-xhigh-fast",
    "gpt-5.3-codex-spark-preview",
    "gpt-5.2",
    "gpt-5.2-codex-low",
    "gpt-5.2-codex",
    "gpt-5.2-codex-fast",
    "gpt-5.2-codex-high",
    "gpt-5.2-codex-xhigh",
    "gpt-5.1-codex-max",
    "gpt-5.1-codex-max-high",
    "gpt-5.2-high",
    "gpt-5.1-high",
    "gpt-5.1-codex-mini",
    "opus-4.6-thinking",
    "opus-4.6",
    "opus-4.5",
    "opus-4.5-thinking",
    "sonnet-4.6",
    "sonnet-4.6-thinking",
    "sonnet-4.5",
    "sonnet-4.5-thinking",
    "gemini-3.1-pro",
    "gemini-3-pro",
    "gemini-3-flash",
    "grok",
    "kimi-k2.5",
)

# 默认模型（来自 paperclip cursor-local/src/index.ts）
DEFAULT_CURSOR_MODEL = "auto"


@dataclass
class AdapterConfig:
    """适配器运行时配置。

    字段含义与 Paperclip `cursor-local` 适配器对齐，
    并补充 N.E.K.O 插件所需的额外选项。
    """

    command: str = ""
    """Cursor Agent CLI 可执行文件路径。空字符串表示自动检测。"""

    model: str = ""
    """默认模型 ID。空字符串表示使用 CLI 默认值（通常为 auto）。"""

    mode: str = ""
    """执行模式："" | "agent" | "build" | "ask" | "browse" 等。空字符串表示使用默认。"""

    yolo: bool = True
    """绕过交互式确认（--yolo 参数）。非交互式环境必须为 true。"""

    timeout_sec: int = 300
    """单次执行超时（秒）。main_server LLM 工具上限 300s。"""

    cwd: str = ""
    """默认工作目录。空字符串表示使用插件进程 cwd。"""

    instructions_file_path: str = ""
    """指令文件路径（markdown）。内容会前置到 stdin 提示。"""

    max_retries: int = 1
    """失败后自动重试新会话的次数。"""

    extra_args: list[str] = field(default_factory=list)
    """额外 CLI 参数。"""

    @classmethod
    def from_config_dict(cls, data: dict[str, Any]) -> "AdapterConfig":
        """从 plugin.toml 的 [cursor] 节构造配置。

        缺失字段使用默认值；类型不匹配时回退到默认值。
        """
        if not isinstance(data, dict):
            return cls()

        def _str(key: str, default: str = "") -> str:
            v = data.get(key, default)
            return v if isinstance(v, str) and v else default

        def _int(key: str, default: int = 0) -> int:
            v = data.get(key, default)
            try:
                return int(v) if v is not None else default
            except (TypeError, ValueError):
                return default

        def _bool(key: str, default: bool = True) -> bool:
            v = data.get(key, default)
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.strip().lower() in ("1", "true", "yes", "on")
            return default

        # extra_args 在 toml 中是 JSON 数组字符串
        extra_args_raw = data.get("extra_args", "[]")
        extra_args: list[str] = []
        if isinstance(extra_args_raw, list):
            extra_args = [str(a) for a in extra_args_raw if isinstance(a, (str, int, float))]
        elif isinstance(extra_args_raw, str):
            try:
                parsed = json.loads(extra_args_raw)
                if isinstance(parsed, list):
                    extra_args = [str(a) for a in parsed if isinstance(a, (str, int, float))]
            except (json.JSONDecodeError, TypeError):
                pass

        return cls(
            command=_str("command"),
            model=_str("model"),
            mode=_str("mode"),
            yolo=_bool("yolo", True),
            timeout_sec=_int("timeout_sec", 300) or 300,
            cwd=_str("cwd"),
            instructions_file_path=_str("instructions_file_path"),
            max_retries=_int("max_retries", 1),
            extra_args=extra_args,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "model": self.model,
            "mode": self.mode,
            "yolo": self.yolo,
            "timeout_sec": self.timeout_sec,
            "cwd": self.cwd,
            "instructions_file_path": self.instructions_file_path,
            "max_retries": self.max_retries,
            "extra_args": list(self.extra_args),
        }


# ---------------------------------------------------------------------------
# 会话记录
# ---------------------------------------------------------------------------


@dataclass
class SessionRecord:
    """单条会话记录。

    用于跨调用恢复 Cursor 会话。会话 ID（session_id）由 Cursor Agent CLI
    在 stream-json 的 result 事件中返回，后续调用通过
    ``--resume <session_id>`` 复用上下文。
    """

    session_id: str
    """Cursor CLI 分配的会话 session_id。"""

    cwd: str
    """会话绑定的工作目录。恢复时必须匹配。"""

    prompt_signature: str
    """提示包签名（instructions 文件的哈希）。

    用于检测提示包变化，变化时放弃旧会话。
    """

    created_at: float
    """会话首次创建的 monotonic 时间戳。"""

    last_used_at: float
    """会话最近一次成功使用的时间戳。"""

    turn_count: int = 0
    """会话累计执行的轮次数。"""

    last_error: str = ""
    """最近一次错误分类（空字符串表示无错误）。"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "cwd": self.cwd,
            "prompt_signature": self.prompt_signature,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "turn_count": self.turn_count,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionRecord":
        return cls(
            session_id=str(data.get("session_id", "")),
            cwd=str(data.get("cwd", "")),
            prompt_signature=str(data.get("prompt_signature", "")),
            created_at=float(data.get("created_at", 0.0)),
            last_used_at=float(data.get("last_used_at", 0.0)),
            turn_count=int(data.get("turn_count", 0)),
            last_error=str(data.get("last_error", "")),
        )


# ---------------------------------------------------------------------------
# 执行结果
# ---------------------------------------------------------------------------


@dataclass
class UsageSummary:
    """Token 使用量与成本统计。

    Cursor 的 result 事件携带 usage（input/cached/output tokens）
    和 total_cost_usd。一次执行可能产生多个 result 事件，需要累加。
    """

    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
        }


@dataclass
class ExecuteResult:
    """一次 Cursor 执行的完整结果。"""

    session_id: str = ""
    """本次执行使用的会话 session_id（可能是新创建或恢复的）。"""

    is_new_session: bool = False
    """是否是新创建的会话（True）还是恢复的旧会话（False）。"""

    final_text: str = ""
    """最后一条 assistant 消息的文本（便于 LLM 直接消费）。"""

    usage: UsageSummary = field(default_factory=UsageSummary)
    """Token 使用量与成本统计。"""

    duration_ms: int = 0
    """本次执行耗时（毫秒）。"""

    error_kind: str = ""
    """错误分类（空字符串表示成功）。参见 errors.py。"""

    error_message: str = ""
    """错误详情。"""

    retry_not_before: str = ""
    """瞬态错误的重试时间（ISO 格式字符串，空表示无限制）。"""

    raw_events: list[dict[str, Any]] = field(default_factory=list)
    """原始事件列表（用于调试，默认不返回给 LLM）。"""

    @property
    def is_error(self) -> bool:
        return bool(self.error_kind)

    def to_llm_payload(self) -> dict[str, Any]:
        """构造返回给 LLM 的精简 payload。"""
        if self.is_error:
            return {
                "output": self.final_text or self.error_message,
                "is_error": True,
                "error": self.error_message,
                "error_kind": self.error_kind,
                "session_id": self.session_id,
                "duration_ms": self.duration_ms,
                "retry_not_before": self.retry_not_before,
            }
        return {
            "output": self.final_text,
            "is_error": False,
            "session_id": self.session_id,
            "is_new_session": self.is_new_session,
            "usage": self.usage.to_dict(),
            "duration_ms": self.duration_ms,
        }


# ---------------------------------------------------------------------------
# CLI 参数构建选项
# ---------------------------------------------------------------------------


@dataclass
class CLIInvocation:
    """一次 Cursor CLI 调用的完整参数。"""

    cmd: list[str]
    """命令行参数列表（含可执行文件路径）。"""

    cwd: str
    """工作目录。"""

    stdin_data: bytes
    """标准输入数据（prompt）。"""

    timeout: float
    """超时（秒）。"""

    env_overrides: dict[str, str] = field(default_factory=dict)
    """环境变量覆盖。"""

    def to_log_dict(self) -> dict[str, Any]:
        """构造日志友好的字典（不包含 stdin 内容）。"""
        return {
            "cmd": self.cmd,
            "cwd": self.cwd,
            "stdin_len": len(self.stdin_data),
            "timeout": self.timeout,
            "env_keys": list(self.env_overrides.keys()),
        }


# ---------------------------------------------------------------------------
# 工具调用参数（LLM 可见）
# ---------------------------------------------------------------------------


CursorMode = Literal["", "agent", "build", "ask", "browse"]
"""Cursor 执行模式。空字符串表示使用配置默认值。"""


__all__ = [
    "CURSOR_KNOWN_MODELS",
    "DEFAULT_CURSOR_MODEL",
    "AdapterConfig",
    "SessionRecord",
    "UsageSummary",
    "ExecuteResult",
    "CLIInvocation",
    "CursorMode",
]
