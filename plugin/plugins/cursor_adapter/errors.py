"""Cursor Adapter — 错误分类。

将 Cursor Agent CLI 执行过程中的各种错误归类为统一的 ``ClassifiedError``，
供执行器和重试逻辑使用。

错误分类参考 paperclip cursor-local 适配器的错误处理，
以及 N.E.K.O codex_adapter 的分类模式。

与 Codex 适配器的差异：
- 无 ``unknown_session`` 概念（Cursor 的 --resume 失败表现不同）
- 认证错误检测 Cursor 特有的未登录提示
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# 错误分类常量
# ---------------------------------------------------------------------------

CLI_NOT_FOUND = "cli_not_found"
"""Cursor Agent CLI 可执行文件未找到。不可重试。"""

TIMEOUT = "timeout"
"""执行超时。不可重试（但可在新会话重试）。"""

AUTH_ERROR = "auth_error"
"""认证失败（未登录 / token 失效）。不可重试。"""

RATE_LIMIT = "rate_limit"
"""速率限制。可重试，通常带 retry_not_before。"""

TRANSIENT_UPSTREAM = "transient_upstream"
"""瞬态上游错误（网络抖动 / 5xx / 连接重置）。可重试。"""

UNKNOWN_SESSION = "unknown_session"
"""会话恢复失败（session_id 失效）。可重试（新建会话）。"""

PERMISSION_DENIED = "permission_denied"
"""权限被拒（文件 / 命令）。不可重试。"""

UNKNOWN = "unknown"
"""未知错误。默认不可重试。"""


# 可重试的错误分类
_RETRYABLE_KINDS: frozenset[str] = frozenset({
    TRANSIENT_UPSTREAM,
    RATE_LIMIT,
    UNKNOWN_SESSION,
})


def is_retryable(kind: str) -> bool:
    """判断错误分类是否可重试。"""
    return kind in _RETRYABLE_KINDS


# ---------------------------------------------------------------------------
# 错误对象
# ---------------------------------------------------------------------------


@dataclass
class ClassifiedError:
    """分类后的错误。

    Attributes
    ----------
    kind:
        错误分类常量（见上）。
    message:
        人类可读的错误消息。
    retryable:
        是否可重试（与 ``is_retryable(kind)`` 一致，缓存避免重复计算）。
    retry_not_before:
        ISO 格式时间字符串。瞬态错误（如速率限制）可能携带，
        表示在此时间之前不应重试。空字符串表示无限制。
    """

    kind: str
    message: str
    retryable: bool = False
    retry_not_before: str = ""


# ---------------------------------------------------------------------------
# 错误分类逻辑
# ---------------------------------------------------------------------------

# 认证错误特征（不区分大小写）
_AUTH_PATTERNS: tuple[str, ...] = (
    "not logged in",
    "not authenticated",
    "authentication failed",
    "unauthorized",
    "invalid token",
    "login required",
    "未登录",
    "认证失败",
    "请先登录",
)

# 速率限制特征
_RATE_LIMIT_PATTERNS: tuple[str, ...] = (
    "rate limit",
    "rate_limit",
    "too many requests",
    "429",
    "速率限制",
    "请求过于频繁",
)

# 未知会话特征
_UNKNOWN_SESSION_PATTERNS: tuple[str, ...] = (
    "session not found",
    "unknown session",
    "invalid session",
    "session expired",
    "会话不存在",
    "会话已过期",
)

# 权限被拒特征
_PERMISSION_PATTERNS: tuple[str, ...] = (
    "permission denied",
    "access denied",
    "operation not permitted",
    "权限不足",
    "拒绝访问",
)

# 瞬态上游错误特征
_TRANSIENT_PATTERNS: tuple[str, ...] = (
    "connection reset",
    "connection refused",
    "econnreset",
    "econnrefused",
    "etimedout",
    "socket hang up",
    "internal server error",
    "bad gateway",
    "service unavailable",
    "gateway timeout",
    "502",
    "503",
    "504",
    "network error",
    "网络错误",
    "连接重置",
)


def _matches_any(text_lower: str, patterns: tuple[str, ...]) -> bool:
    return any(p in text_lower for p in patterns)


def classify_error(
    message: str,
    *,
    stdout: str = "",
    stderr: str = "",
    return_code: Optional[int] = None,
) -> ClassifiedError:
    """将原始错误信息分类为 ``ClassifiedError``。

    按优先级依次检测：认证 → 速率限制 → 未知会话 → 权限 → 瞬态 → 默认未知。
    """
    haystack = "\n".join(part for part in (message, stdout, stderr) if part)
    haystack_lower = haystack.lower()

    # 认证错误（最高优先级，重试无意义）
    if _matches_any(haystack_lower, _AUTH_PATTERNS):
        return ClassifiedError(
            kind=AUTH_ERROR,
            message=message.strip() or "Cursor authentication failed (not logged in?)",
            retryable=False,
        )

    # 速率限制
    if _matches_any(haystack_lower, _RATE_LIMIT_PATTERNS):
        return ClassifiedError(
            kind=RATE_LIMIT,
            message=message.strip() or "Cursor rate limited",
            retryable=True,
        )

    # 未知会话（resume 失效）
    if _matches_any(haystack_lower, _UNKNOWN_SESSION_PATTERNS):
        return ClassifiedError(
            kind=UNKNOWN_SESSION,
            message=message.strip() or "Cursor session not found",
            retryable=True,
        )

    # 权限被拒
    if _matches_any(haystack_lower, _PERMISSION_PATTERNS):
        return ClassifiedError(
            kind=PERMISSION_DENIED,
            message=message.strip() or "Permission denied",
            retryable=False,
        )

    # 瞬态上游错误
    if _matches_any(haystack_lower, _TRANSIENT_PATTERNS):
        return ClassifiedError(
            kind=TRANSIENT_UPSTREAM,
            message=message.strip() or "Transient upstream error",
            retryable=True,
        )

    # 默认：未知错误
    return ClassifiedError(
        kind=UNKNOWN,
        message=message.strip() or f"Cursor execution failed (exit code {return_code})",
        retryable=False,
    )


__all__ = [
    # 常量
    "CLI_NOT_FOUND",
    "TIMEOUT",
    "AUTH_ERROR",
    "RATE_LIMIT",
    "TRANSIENT_UPSTREAM",
    "UNKNOWN_SESSION",
    "PERMISSION_DENIED",
    "UNKNOWN",
    # 函数
    "is_retryable",
    "classify_error",
    # 类型
    "ClassifiedError",
]
