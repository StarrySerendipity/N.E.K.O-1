"""Feishu Adapter — 数据模型。

配置、消息、发送结果。参考飞书开放平台文档：
https://open.feishu.cn/document/server-docs/im-v1/message/create
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import json
import time


@dataclass
class AdapterConfig:
    """飞书适配器配置。"""
    app_id: str = ""
    app_secret: str = ""
    encrypt_key: str = ""
    verification_token: str = ""
    connection_mode: str = "websocket"  # websocket 或 webhook
    webhook_port: int = 7777
    webhook_path: str = "/feishu/webhook"
    log_level: str = "INFO"

    @classmethod
    def from_config_dict(cls, data: dict[str, Any]) -> "AdapterConfig":
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

        return cls(
            app_id=_str("app_id"),
            app_secret=_str("app_secret"),
            encrypt_key=_str("encrypt_key"),
            verification_token=_str("verification_token"),
            connection_mode=_str("connection_mode", "websocket"),
            webhook_port=_int("webhook_port", 7777),
            webhook_path=_str("webhook_path", "/feishu/webhook"),
            log_level=_str("log_level", "INFO"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "app_secret": "***" if self.app_secret else "",
            "encrypt_key": "***" if self.encrypt_key else "",
            "verification_token": "***" if self.verification_token else "",
            "connection_mode": self.connection_mode,
            "webhook_port": self.webhook_port,
            "webhook_path": self.webhook_path,
            "log_level": self.log_level,
        }


@dataclass
class FeishuMessage:
    """飞书消息模型。"""
    message_id: str = ""
    chat_id: str = ""
    chat_type: str = ""  # p2p 或 group
    sender_id: str = ""
    sender_type: str = ""  # user 或 bot
    msg_type: str = ""  # text, image, file, audio, media, sticker, interactive, post, share_chat, share_user
    content: str = ""  # JSON 字符串
    create_time: str = ""  # 时间戳（毫秒）
    update_time: str = ""
    parent_id: str = ""  # 回复消息 ID
    root_id: str = ""  # 话题根消息 ID

    @classmethod
    def from_feishu_event(cls, data: Any) -> "FeishuMessage":
        """从飞书事件数据创建消息对象。"""
        if not hasattr(data, "event"):
            return cls()

        event = data.event
        message = getattr(event, "message", None)
        sender = getattr(event, "sender", None)

        if message is None:
            return cls()

        return cls(
            message_id=str(getattr(message, "message_id", "") or ""),
            chat_id=str(getattr(message, "chat_id", "") or ""),
            chat_type=str(getattr(message, "chat_type", "") or ""),
            sender_id=str(
                getattr(sender, "sender_id", {})
                .get("open_id", "")
                or ""
            ) if sender else "",
            sender_type=str(getattr(sender, "sender_type", "") or "") if sender else "",
            msg_type=str(getattr(message, "message_type", "") or ""),
            content=str(getattr(message, "content", "") or ""),
            create_time=str(getattr(message, "create_time", "") or ""),
            update_time=str(getattr(message, "update_time", "") or ""),
            parent_id=str(getattr(message, "parent_id", "") or ""),
            root_id=str(getattr(message, "root_id", "") or ""),
        )

    def get_text_content(self) -> str:
        """提取文本内容。"""
        if self.msg_type != "text":
            return ""
        try:
            content_dict = json.loads(self.content)
            return content_dict.get("text", "")
        except (json.JSONDecodeError, TypeError):
            return self.content

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "chat_type": self.chat_type,
            "sender_id": self.sender_id,
            "sender_type": self.sender_type,
            "msg_type": self.msg_type,
            "content": self.content,
            "create_time": self.create_time,
            "parent_id": self.parent_id,
            "root_id": self.root_id,
        }


@dataclass
class SendMessageResult:
    """消息发送结果。"""
    success: bool = False
    message_id: str = ""
    chat_id: str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "error_message": self.error_message,
        }


@dataclass
class SessionRecord:
    """会话记录。"""
    session_id: str
    chat_id: str
    user_id: str
    created_at: float
    last_used_at: float
    message_count: int = 0
    last_message_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "message_count": self.message_count,
            "last_message_type": self.last_message_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionRecord":
        return cls(
            session_id=str(data.get("session_id", "")),
            chat_id=str(data.get("chat_id", "")),
            user_id=str(data.get("user_id", "")),
            created_at=float(data.get("created_at", 0.0)),
            last_used_at=float(data.get("last_used_at", 0.0)),
            message_count=int(data.get("message_count", 0)),
            last_message_type=str(data.get("last_message_type", "")),
        )


__all__ = [
    "AdapterConfig",
    "FeishuMessage",
    "SendMessageResult",
    "SessionRecord",
]
