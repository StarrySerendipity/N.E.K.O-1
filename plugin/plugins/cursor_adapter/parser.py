"""Cursor Adapter — stream-json 输出解析器。

Cursor Agent CLI 在 ``-p --output-format stream-json`` 模式下，
每行输出一个 JSON 事件。事件类型包括（来自 paperclip cursor-local parse.ts）：

- ``assistant``：助手消息，``message`` 含文本（``message.text`` 或
  ``message.content[].text``，content part type 为 ``output_text`` / ``text``）
- ``result``：结果事件，含 ``usage``（token 用量）、``total_cost_usd``、
  ``is_error``、``result`` 文本、``session_id``
- ``error``：CLI 错误，含 ``message`` / ``error`` / ``detail``
- ``system``：系统事件，``subtype == "error"`` 时为错误

会话 ID（session_id）可出现在任意事件的 ``session_id`` / ``sessionId`` /
``sessionID`` 字段，解析器会持续捕获。

与 Codex 适配器的差异：
- 会话 ID 字段为 ``session_id``（而非 ``thread_id``），从 result 事件读取
- 助手消息在 ``assistant`` 事件的 ``message`` 中（而非 ``item.completed``）
- token 使用量在 ``result`` 事件（而非 ``turn.completed``），且携带 ``cost_usd``
- 错误事件为 ``error`` / ``system(subtype=error)``（而非 ``turn.failed``）
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
class AssistantEvent:
    """``assistant`` 事件 — 助手消息。"""

    text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResultEvent:
    """``result`` 事件 — 执行结果，含 usage / cost / session_id。"""

    usage: UsageSummary = field(default_factory=UsageSummary)
    cost_usd: float = 0.0
    is_error: bool = False
    result_text: str = ""
    session_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorEvent:
    """``error`` 或 ``system(subtype=error)`` 事件。"""

    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedCursorStream:
    """一次完整 Cursor stream-json 输出的解析结果。"""

    assistant_messages: list[AssistantEvent] = field(default_factory=list)
    """所有 assistant 事件（按出现顺序）。"""

    results: list[ResultEvent] = field(default_factory=list)
    """所有 result 事件。"""

    errors: list[ErrorEvent] = field(default_factory=list)
    """所有 error / system-error 事件。"""

    session_id: str = ""
    """捕获到的 session_id（来自任意事件，最后出现的为准）。"""

    parse_errors: list[str] = field(default_factory=list)
    """无法解析的行（用于调试）。"""

    # ------------------------------------------------------------------
    # 便捷属性
    # ------------------------------------------------------------------

    @property
    def final_text(self) -> str:
        """最后一条 assistant 消息的文本。

        与 paperclip parseCursorJsonl 的行为一致：每遇到非空消息就覆盖。
        若无 assistant 消息但 result 携带文本，则用 result 文本兜底。
        """
        for msg in reversed(self.assistant_messages):
            if msg.text:
                return msg.text
        # result 事件可能携带 result 文本（无 assistant 消息时）
        for res in reversed(self.results):
            if res.result_text:
                return res.result_text
        return ""

    @property
    def error_message(self) -> str:
        """错误消息（最后一个 error / system-error 事件）。"""
        for ev in reversed(self.errors):
            if ev.message:
                return ev.message
        # result 事件标记 is_error 时也算错误
        for res in reversed(self.results):
            if res.is_error and res.result_text:
                return res.result_text
        return ""

    @property
    def total_usage(self) -> UsageSummary:
        """累加所有 result 事件的 token 用量与成本。"""
        total = UsageSummary()
        for ev in self.results:
            total.input_tokens += ev.usage.input_tokens
            total.cached_input_tokens += ev.usage.cached_input_tokens
            total.output_tokens += ev.usage.output_tokens
            total.cost_usd += ev.cost_usd
        return total

    @property
    def is_error(self) -> bool:
        """是否包含错误事件或 result 标记 is_error。"""
        if self.errors:
            return True
        return any(res.is_error for res in self.results)


# ---------------------------------------------------------------------------
# 解析器
# ---------------------------------------------------------------------------


class CursorOutputParser:
    """Cursor Agent CLI stream-json 输出解析器。

    用法::

        parser = CursorOutputParser()
        async for line in process.stdout:
            parser.parse_line(line)
        stream = parser.finalize()

    解析器是有状态的：会累积所有事件，``finalize()`` 返回汇总结果。
    """

    def __init__(self) -> None:
        self._assistant_messages: list[AssistantEvent] = []
        self._results: list[ResultEvent] = []
        self._errors: list[ErrorEvent] = []
        self._session_id: str = ""
        self._parse_errors: list[str] = []
        self._max_parse_errors = 100

    # ------------------------------------------------------------------
    # 逐行解析
    # ------------------------------------------------------------------

    def parse_line(self, line: str | bytes) -> Optional[Any]:
        """解析一行输出，返回对应的事件对象。

        无法解析的行会被记录到 parse_errors，返回 None。
        空行返回 None。
        """
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
            # 非 JSON 行（可能是 CLI 的调试输出或日志）
            if len(self._parse_errors) < self._max_parse_errors:
                self._parse_errors.append(line[:200])
            return None

        if not isinstance(payload, dict):
            if len(self._parse_errors) < self._max_parse_errors:
                self._parse_errors.append(f"non-object: {line[:200]}")
            return None

        # 持续捕获 session_id（可出现在任意事件中）
        found_session = _read_session_id(payload)
        if found_session:
            self._session_id = found_session

        event_type = str(payload.get("type", "")).strip()

        if event_type == "assistant":
            return self._handle_assistant(payload)
        if event_type == "result":
            return self._handle_result(payload)
        if event_type == "error":
            return self._handle_error(payload)
        if event_type == "system":
            return self._handle_system(payload)

        # 未知事件类型 — 忽略（前向兼容）
        return None

    def _handle_assistant(self, payload: dict[str, Any]) -> AssistantEvent:
        text_parts = _collect_assistant_text(payload.get("message"))
        text = "\n".join(t for t in text_parts if t)
        event = AssistantEvent(text=text, raw=payload)
        self._assistant_messages.append(event)
        return event

    def _handle_result(self, payload: dict[str, Any]) -> ResultEvent:
        usage_obj = payload.get("usage")
        if not isinstance(usage_obj, dict):
            usage_obj = {}

        usage = UsageSummary(
            input_tokens=_as_int(usage_obj.get("input_tokens", usage_obj.get("inputTokens"))),
            cached_input_tokens=_as_int(
                usage_obj.get("cached_input_tokens",
                              usage_obj.get("cachedInputTokens",
                                            usage_obj.get("cache_read_input_tokens")))
            ),
            output_tokens=_as_int(usage_obj.get("output_tokens", usage_obj.get("outputTokens"))),
        )

        cost_usd = _as_float(
            payload.get("total_cost_usd",
                        payload.get("cost_usd",
                                    payload.get("cost")))
        )

        is_error = payload.get("is_error") is True
        subtype = str(payload.get("subtype", "")).strip().lower()
        if subtype == "error":
            is_error = True

        result_text = str(payload.get("result", "")).strip()

        session_id = _read_session_id(payload) or ""

        event = ResultEvent(
            usage=usage,
            cost_usd=cost_usd,
            is_error=is_error,
            result_text=result_text,
            session_id=session_id,
            raw=payload,
        )
        self._results.append(event)
        return event

    def _handle_error(self, payload: dict[str, Any]) -> ErrorEvent:
        message = _as_error_text(
            payload.get("message",
                        payload.get("error",
                                    payload.get("detail")))
        )
        event = ErrorEvent(message=message, raw=payload)
        self._errors.append(event)
        return event

    def _handle_system(self, payload: dict[str, Any]) -> Optional[ErrorEvent]:
        subtype = str(payload.get("subtype", "")).strip().lower()
        if subtype != "error":
            return None
        message = _as_error_text(
            payload.get("message",
                        payload.get("error",
                                    payload.get("detail")))
        )
        event = ErrorEvent(message=message, raw=payload)
        self._errors.append(event)
        return event

    # ------------------------------------------------------------------
    # 完成解析
    # ------------------------------------------------------------------

    def finalize(self) -> ParsedCursorStream:
        """返回完整的解析结果。调用后解析器状态不变，可继续解析。"""
        return ParsedCursorStream(
            assistant_messages=list(self._assistant_messages),
            results=list(self._results),
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
    """从事件中读取 session_id（兼容多种命名）。"""
    for key in ("session_id", "sessionId", "sessionID"):
        val = event.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _collect_assistant_text(message: Any) -> list[str]:
    """从 assistant 事件的 message 字段收集文本。

    message 可能是：
    - 字符串：直接返回
    - 对象：``message.text`` + ``message.content[]`` 中 type 为
      ``output_text`` / ``text`` 的 part 的 text
    """
    if isinstance(message, str):
        trimmed = message.strip()
        return [trimmed] if trimmed else []

    if not isinstance(message, dict):
        return []

    lines: list[str] = []
    direct = str(message.get("text", "")).strip()
    if direct:
        lines.append(direct)

    content = message.get("content")
    if isinstance(content, list):
        for part_raw in content:
            if not isinstance(part_raw, dict):
                continue
            part_type = str(part_raw.get("type", "")).strip()
            if part_type in ("output_text", "text"):
                text = str(part_raw.get("text", "")).strip()
                if text:
                    lines.append(text)

    return lines


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


def parse_cursor_jsonl(stdout: str) -> ParsedCursorStream:
    """一次性解析整段 stdout 文本。

    对于流式场景，建议使用 ``CursorOutputParser`` 逐行解析；
    本函数适用于已有完整 stdout 文本的场景（如单元测试）。
    """
    parser = CursorOutputParser()
    for line in stdout.splitlines():
        parser.parse_line(line)
    return parser.finalize()


# ---------------------------------------------------------------------------
# 流式回调类型
# ---------------------------------------------------------------------------


StreamCallback = Callable[[Any], None]
"""流式事件回调。可以是同步或异步函数。"""


__all__ = [
    # 事件类型
    "AssistantEvent",
    "ResultEvent",
    "ErrorEvent",
    "ParsedCursorStream",
    # 解析器
    "CursorOutputParser",
    "parse_cursor_jsonl",
    # 类型
    "StreamCallback",
]
