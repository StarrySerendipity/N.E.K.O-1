"""OpenCode Adapter — 数据模型。

定义适配器运行所需的配置、会话、执行结果等数据结构。
所有结构都是纯 dataclass，不依赖 SDK 内部类型。

字段含义与 Paperclip `opencode-local` 适配器对齐，
并补充 N.E.K.O 插件所需的额外选项。

与 Cursor 适配器的关键差异：
- 命令：``opencode run --format json --model <provider/model> [--session <id>]``
- 模型格式：``provider/model``（如 ``anthropic/claude-sonnet-4-20250514``）
- 会话 ID：``--session <id>``（而非 ``--resume <id>``）
- 推理变体：``--variant <low|medium|high>``（而非 ``--mode``）
- 输出格式：JSONL（而非 stream-json），每行一个 JSON 对象
- 安装：``npm install -g opencode-ai``（无需平台特定二进制）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# 适配器配置
# ---------------------------------------------------------------------------


# OpenCode 默认模型（来自 paperclip opencode-local/src/index.ts）
DEFAULT_OPENCODE_MODEL = "anthropic/claude-sonnet-4-20250514"

# 推理变体（来自 paperclip opencode-local 的 variant 概念）
OPENCODE_VARIANTS: tuple[str, ...] = ("", "low", "medium", "high")


@dataclass
class AdapterConfig:
    """适配器运行时配置。

    字段含义与 Paperclip ``opencode-local`` 适配器对齐。
    """

    command: str = ""
    """OpenCode CLI 可执行文件路径。空字符串表示自动检测（PATH 上的 opencode）。"""

    model: str = ""
    """默认模型 ID（provider/model 格式）。空字符串使用默认。"""

    variant: str = ""
    """推理变体："" | "low" | "medium" | "high"。空字符串使用默认。"""

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
        """从 plugin.toml 的 [opencode] 节构造配置。"""
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
            variant=_str("variant"),
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
            "variant": self.variant,
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

    用于跨调用恢复 OpenCode 会话。会话 ID（sessionID）由 OpenCode CLI
    在 JSONL 输出的事件中携带，后续调用通过 ``--session <id>`` 复用上下文。
    """

    session_id: str
    """OpenCode CLI 分配的会话 sessionID。"""

    cwd: str
    """会话绑定的工作目录。恢复时必须匹配。"""

    prompt_signature: str
    """提示包签名（instructions 文件的哈希）。用于检测提示包变化。"""

    created_at: float
    """会话首次创建的时间戳。"""

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

    OpenCode 的 step_finish 事件携带 tokens（input / cache.read / output）
    和 cost（totalCost）。一次执行可能产生多个 step_finish 事件，需要累加。
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
    """一次 OpenCode 执行的完整结果。"""

    session_id: str = ""
    """本次执行使用的会话 sessionID（可能是新创建或恢复的）。"""

    is_new_session: bool = False
    """是否是新创建的会话（True）还是恢复的旧会话（False）。"""

    final_text: str = ""
    """助手消息的文本（便于 LLM 直接消费）。"""

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
    """一次 OpenCode CLI 调用的完整参数。"""

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


__all__ = [
    "DEFAULT_OPENCODE_MODEL",
    "OPENCODE_VARIANTS",
    "AdapterConfig",
    "SessionRecord",
    "UsageSummary",
    "ExecuteResult",
    "CLIInvocation",
]