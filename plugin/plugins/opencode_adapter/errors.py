"""OpenCode Adapter — 错误分类。

将 OpenCode CLI 执行过程中的各种错误归类为统一的 ``ClassifiedError``，
供执行器和重试逻辑使用。

错误分类参考 paperclip opencode-local 适配器的错误处理，
以及 N.E.K.O cursor_adapter 的分类模式。

与 Cursor 适配器的差异：
- 会话 ID 为 ``sessionID``（而非 ``session_id``），从 JSONL 事件读取
- 未知会话错误检测 ``isOpenCodeUnknownSessionError`` 模式
- OpenCode 特有错误：provider 不可用、模型不可用
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# 错误分类常量
# ---------------------------------------------------------------------------

CLI_NOT_FOUND = "cli_not_found"
"""OpenCode CLI 可执行文件未找到。不可重试。"""

TIMEOUT = "timeout"
"""执行超时。不可重试（但可在新会话重试）。"""

AUTH_ERROR = "auth_error"
"""认证失败（API key 无效 / 未配置）。不可重试。"""

RATE_LIMIT = "rate_limit"
"""速率限制。可重试，通常带 retry_not_before。"""

TRANSIENT_UPSTREAM = "transient_upstream"
"""瞬态上游错误（网络抖动 / 5xx / 连接重置）。可重试。"""

UNKNOWN_SESSION = "unknown_session"
"""会话恢复失败（sessionID 失效）。可重试（新建会话）。"""

PROVIDER_UNAVAILABLE = "provider_unavailable"
"""Provider 不可用（模型未注册 / provider 未配置）。不可重试。"""

MODEL_UNAVAILABLE = "model_not_available"
"""模型不可用（模型 ID 不在 provider 的模型列表中）。不可重试。"""

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
    """分类后的错误。"""

    kind: str
    message: str
    retryable: bool = False
    retry_not_before: str = ""


# ---------------------------------------------------------------------------
# 错误分类逻辑
# ---------------------------------------------------------------------------

# 认证错误特征
_AUTH_PATTERNS: tuple[str, ...] = (
    "not logged in",
    "not authenticated",
    "authentication failed",
    "unauthorized",
    "invalid api key",
    "invalid token",
    "login required",
    "请先登录",
    "认证失败",
    "api key not found",
    "no api key",
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

# 未知会话特征（来自 paperclip opencode-local parse.ts 的 isOpenCodeUnknownSessionError）
_UNKNOWN_SESSION_PATTERNS: tuple[str, ...] = (
    "session not found",
    "unknown session",
    "invalid session",
    "session expired",
    "no session",
    "会话不存在",
    "会话已过期",
    "session_id",
    "sessionID",
    "sessionId",
)

# Provider 不可用特征
_PROVIDER_UNAVAILABLE_PATTERNS: tuple[str, ...] = (
    "provider not found",
    "unknown provider",
    "provider unavailable",
    "no provider configured",
)

# 模型不可用特征
_MODEL_UNAVAILABLE_PATTERNS: tuple[str, ...] = (
    "model not found",
    "model not available",
    "unknown model",
    "model unavailable",
    "invalid model",
    "no model",
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
    "dns",
    "econn",
    "enotfound",
    "eai_again",
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

    按优先级依次检测：认证 → Provider不可用 → 模型不可用 → 速率限制 → 未知会话 → 权限 → 瞬态 → 默认未知。
    """
    haystack = "\n".join(part for part in (message, stdout, stderr) if part)
    haystack_lower = haystack.lower()

    # 认证错误（最高优先级，重试无意义）
    if _matches_any(haystack_lower, _AUTH_PATTERNS):
        return ClassifiedError(
            kind=AUTH_ERROR,
            message=message.strip() or "OpenCode authentication failed (API key not configured?)",
            retryable=False,
        )

    # Provider 不可用
    if _matches_any(haystack_lower, _PROVIDER_UNAVAILABLE_PATTERNS):
        return ClassifiedError(
            kind=PROVIDER_UNAVAILABLE,
            message=message.strip() or "OpenCode provider not available",
            retryable=False,
        )

    # 模型不可用
    if _matches_any(haystack_lower, _MODEL_UNAVAILABLE_PATTERNS):
        return ClassifiedError(
            kind=MODEL_UNAVAILABLE,
            message=message.strip() or "OpenCode model not available",
            retryable=False,
        )

    # 速率限制
    if _matches_any(haystack_lower, _RATE_LIMIT_PATTERNS):
        return ClassifiedError(
            kind=RATE_LIMIT,
            message=message.strip() or "OpenCode rate limited",
            retryable=True,
        )

    # 未知会话（resume 失效）
    if _matches_any(haystack_lower, _UNKNOWN_SESSION_PATTERNS):
        return ClassifiedError(
            kind=UNKNOWN_SESSION,
            message=message.strip() or "OpenCode session not found",
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
        message=message.strip() or f"OpenCode execution failed (exit code {return_code})",
        retryable=False,
    )


__all__ = [
    "CLI_NOT_FOUND",
    "TIMEOUT",
    "AUTH_ERROR",
    "RATE_LIMIT",
    "TRANSIENT_UPSTREAM",
    "UNKNOWN_SESSION",
    "PROVIDER_UNAVAILABLE",
    "MODEL_UNAVAILABLE",
    "PERMISSION_DENIED",
    "UNKNOWN",
    "is_retryable",
    "classify_error",
    "ClassifiedError",
]