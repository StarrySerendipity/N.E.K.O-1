"""OpenCode Adapter — JSONL 输出解析器。

OpenCode CLI 在 ``--format json`` 模式下，每行输出一个 JSON 事件。
事件类型包括（来自 paperclip opencode-local parse.ts 的 parseOpenCodeJsonl）：

- ``text``：助手消息，``part.text`` 含文本
- ``step_finish``：步骤完成，含 ``part.tokens``（token 用量）、``part.cost``（totalCost）
- ``tool_use``：工具调用，含 ``part.tool`` 工具名、``part.state`` 状态
- ``error``：CLI 错误，含 ``error`` / ``message``
- ``step_start``：步骤开始，含 ``sessionID``

会话 ID（sessionID）可出现在任意事件中，解析器会持续捕获。

与 Cursor 适配器的差异：
- 会话 ID 字段为 ``sessionID``（而非 ``session_id``），从任意事件读取
- 助手消息在 ``text`` 事件的 ``part.text`` 中（而非 ``assistant`` 事件）
- token 使用量在 ``step_finish`` 事件（而非 ``result`` 事件）
- 成本在 ``step_finish`` 的 ``part.cost.totalCost`` 或 ``part.cost.total_cost``
- 错误事件为 ``error`` 类型
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .models import UsageSummary


# ---------------------------------------------------------------------------
# 事件类型
# ---------------------------------------------------------------------------


@dataclass
class TextEvent:
    """``text`` 事件 — 助手文本消息。"""

    text: str = ""
    session_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepFinishEvent:
    """``step_finish`` 事件 — 步骤完成，含 usage / cost。"""

    usage: UsageSummary = field(default_factory=UsageSummary)
    cost_usd: float = 0.0
    session_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorEvent:
    """``error`` 事件。"""

    message: str = ""
    session_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedOpenCodeStream:
    """一次完整 OpenCode JSONL 输出的解析结果。"""

    text_messages: list[TextEvent] = field(default_factory=list)
    """所有 text 事件（按出现顺序）。"""

    step_finishes: list[StepFinishEvent] = field(default_factory=list)
    """所有 step_finish 事件。"""

    errors: list[ErrorEvent] = field(default_factory=list)
    """所有 error 事件。"""

    session_id: str = ""
    """捕获到的 sessionID（来自任意事件，最后出现的为准）。"""

    parse_errors: list[str] = field(default_factory=list)
    """无法解析的行（用于调试）。"""

    # ------------------------------------------------------------------
    # 便捷属性
    # ------------------------------------------------------------------

    @property
    def final_text(self) -> str:
        """最后一条 text 消息的文本。

        与 paperclip parseOpenCodeJsonl 的行为一致：每遇到非空消息就覆盖。
        """
        for msg in reversed(self.text_messages):
            if msg.text:
                return msg.text
        return ""

    @property
    def error_message(self) -> str:
        """错误消息（最后一个 error 事件）。"""
        for ev in reversed(self.errors):
            if ev.message:
                return ev.message
        return ""

    @property
    def total_usage(self) -> UsageSummary:
        """累加所有 step_finish 事件的 token 用量与成本。"""
        total = UsageSummary()
        for ev in self.step_finishes:
            total.input_tokens += ev.usage.input_tokens
            total.cached_input_tokens += ev.usage.cached_input_tokens
            total.output_tokens += ev.usage.output_tokens
            total.cost_usd += ev.cost_usd
        return total

    @property
    def is_error(self) -> bool:
        """是否包含错误事件。"""
        return bool(self.errors)


# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------


class OpenCodeOutputParser:
    """OpenCode CLI JSONL 输出解析器。

    用法::

        parser = OpenCodeOutputParser()
        async for line in process.stdout:
            parser.parse_line(line)
        stream = parser.finalize()
    """

    def __init__(self) -> None:
        self._text_messages: list[TextEvent] = []
        self._step_finishes: list[StepFinishEvent] = []
        self._errors: list[ErrorEvent] = []
        self._session_id: str = ""
        self._parse_errors: list[str] = []
        self._max_parse_errors = 100

    # ------------------------------------------------------------------
    # 逐行解析
    # ------------------------------------------------------------------

    def parse_line(self, line: str | bytes) -> Optional[Any]:
        """解析一行输出，返回对应的事件对象。"""
        if isinstance(line, bytes):
            try:
                line = line.decode("utf-8", errors="replace")
            except Exception:
                return None

        line = line.strip()
        if not line:
            return None

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            if len(self._parse_errors) < self._max_parse_errors:
                self._parse_errors.append(line[:200])
            return None

        if not isinstance(payload, dict):
            if len(self._parse_errors) < self._max_parse_errors:
                self._parse_errors.append(f"non-object: {line[:200]}")
            return None

        # 持续捕获 sessionID（可出现在任意事件中）
        found_session = _read_session_id(payload)
        if found_session:
            self._session_id = found_session

        event_type = str(payload.get("type", "")).strip()

        if event_type == "text":
            return self._handle_text(payload)
        if event_type == "step_finish":
            return self._handle_step_finish(payload)
        if event_type == "error":
            return self._handle_error(payload)
        # step_start, tool_use, reasoning 等事件目前忽略，但 sessionID 已捕获
        return None

    def _handle_text(self, payload: dict[str, Any]) -> TextEvent:
        part = payload.get("part")
        if not isinstance(part, dict):
            part = {}
        text = str(part.get("text", "")).strip()
        session_id = _read_session_id(payload) or ""
        event = TextEvent(text=text, session_id=session_id, raw=payload)
        self._text_messages.append(event)
        return event

    def _handle_step_finish(self, payload: dict[str, Any]) -> StepFinishEvent:
        part = payload.get("part")
        if not isinstance(part, dict):
            part = {}

        # token 用量（来自 paperclip parseOpenCodeJsonl）
        tokens = part.get("tokens")
        if not isinstance(tokens, dict):
            tokens = {}
        cache = tokens.get("cache")
        if not isinstance(cache, dict):
            cache = {}

        usage = UsageSummary(
            input_tokens=_as_int(tokens.get("input")),
            cached_input_tokens=_as_int(cache.get("read")),
            output_tokens=_as_int(tokens.get("output")),
        )

        # 成本（来自 paperclip parseOpenCodeJsonl）
        cost = part.get("cost")
        if not isinstance(cost, dict):
            cost = {}
        cost_usd = _as_float(
            cost.get("totalCost") or cost.get("total_cost") or cost.get("total")
        )

        session_id = _read_session_id(payload) or ""

        event = StepFinishEvent(
            usage=usage,
            cost_usd=cost_usd,
            session_id=session_id,
            raw=payload,
        )
        self._step_finishes.append(event)
        return event

    def _handle_error(self, payload: dict[str, Any]) -> ErrorEvent:
        message = _as_error_text(payload.get("error") or payload.get("message"))
        session_id = _read_session_id(payload) or ""
        event = ErrorEvent(message=message, session_id=session_id, raw=payload)
        self._errors.append(event)
        return event

    # ------------------------------------------------------------------
    # 完成解析
    # ------------------------------------------------------------------

    def finalize(self) -> ParsedOpenCodeStream:
        """返回完整的解析结果。"""
        return ParsedOpenCodeStream(
            text_messages=list(self._text_messages),
            step_finishes=list(self._step_finishes),
            errors=list(self._errors),
            session_id=self._session_id,
            parse_errors=list(self._parse_errors),
        )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _as_int(value: Any) -> int:
    """安全转换为非负整数。"""
    if value is None:
        return 0
    try:
        n = int(value)
        return n if n > 0 else 0
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    """安全转换为非负浮点数。"""
    if value is None:
        return 0.0
    try:
        f = float(value)
        return f if f > 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def _read_session_id(event: dict[str, Any]) -> Optional[str]:
    """从事件中读取 sessionID（兼容多种命名）。

    来自 paperclip opencode-local parse.ts 的读取逻辑。
    """
    for key in ("sessionID", "sessionId", "session_id"):
        val = event.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _as_error_text(value: Any) -> str:
    """将错误字段转为可读文本。"""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("message", "error", "code", "detail"):
            v = value.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return ""
    if value is None:
        return ""
    return str(value).strip()


def parse_opencode_jsonl(stdout: str) -> ParsedOpenCodeStream:
    """一次性解析整段 stdout 文本。

    对于流式场景，建议使用 ``OpenCodeOutputParser`` 逐行解析；
    本函数适用于已有完整 stdout 文本的场景（如单元测试）。
    """
    parser = OpenCodeOutputParser()
    for line in stdout.splitlines():
        parser.parse_line(line)
    return parser.finalize()


# ---------------------------------------------------------------------------
# 流式回调类型
# ---------------------------------------------------------------------------


StreamCallback = Callable[[Any], None]
"""流式事件回调。可以是同步或异步函数。"""


__all__ = [
    "TextEvent",
    "StepFinishEvent",
    "ErrorEvent",
    "ParsedOpenCodeStream",
    "OpenCodeOutputParser",
    "parse_opencode_jsonl",
    "StreamCallback",
]