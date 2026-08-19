"""Feishu Adapter — 错误分类。"""

from __future__ import annotations

from dataclasses import dataclass


# 错误类型常量
CONFIG_MISSING = "config_missing"
AUTH_ERROR = "auth_error"
TRANSIENT_UPSTREAM = "transient_upstream"
TIMEOUT = "timeout"
RATE_LIMITED = "rate_limited"
INVALID_REQUEST = "invalid_request"
UNKNOWN = "unknown"

# 可重试的错误类型
_RETRYABLE = frozenset({TRANSIENT_UPSTREAM, RATE_LIMITED})


def is_retryable(kind: str) -> bool:
    """判断错误是否可重试。"""
    return kind in _RETRYABLE


@dataclass
class ClassifiedError:
    """分类后的错误。"""
    kind: str
    message: str
    retryable: bool = False
    retry_not_before: str = ""  # ISO 时间戳，表示最早重试时间


def classify_error(message: str) -> ClassifiedError:
    """根据错误消息分类错误类型。"""
    m = message.lower()

    # 连接相关错误
    if any(p in m for p in (
        "connection refused",
        "connection reset",
        "econnrefused",
        "econnreset",
        "connection closed",
        "network is unreachable",
    )):
        return ClassifiedError(TRANSIENT_UPSTREAM, message, retryable=True)

    # 超时错误
    if any(p in m for p in ("timeout", "timed out")):
        return ClassifiedError(TIMEOUT, message, retryable=False)

    # 认证错误
    if any(p in m for p in (
        "auth",
        "unauthorized",
        "forbidden",
        "401",
        "403",
        "invalid app_id",
        "invalid app_secret",
    )):
        return ClassifiedError(AUTH_ERROR, message, retryable=False)

    # 速率限制
    if any(p in m for p in (
        "rate limit",
        "too many requests",
        "429",
        "frequency limit",
    )):
        return ClassifiedError(RATE_LIMITED, message, retryable=True)

    # 无效请求
    if any(p in m for p in (
        "invalid request",
        "bad request",
        "400",
        "param missing",
        "param invalid",
    )):
        return ClassifiedError(INVALID_REQUEST, message, retryable=False)

    return ClassifiedError(UNKNOWN, message, retryable=False)


__all__ = [
    "CONFIG_MISSING",
    "AUTH_ERROR",
    "TRANSIENT_UPSTREAM",
    "TIMEOUT",
    "RATE_LIMITED",
    "INVALID_REQUEST",
    "UNKNOWN",
    "is_retryable",
    "classify_error",
    "ClassifiedError",
]
