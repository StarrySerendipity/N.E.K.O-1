"""Feishu Adapter — 消息处理器。

负责：
1. 处理接收到的飞书消息
2. 将消息转换为内部格式
3. 发布到消息总线
4. 管理会话状态
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from .client import FeishuClient
from .models import FeishuMessage, SessionRecord


class MessageHandler:
    """飞书消息处理器。"""

    def __init__(
        self,
        client: FeishuClient,
        store: Any = None,
        logger: Any = None,
        ctx: Any = None,
    ) -> None:
        self.client = client
        self.store = store
        self.logger = logger
        self.ctx = ctx
        self._lock = asyncio.Lock()
        self._sessions: dict[str, SessionRecord] = {}

    async def handle_incoming_message(self, data: Any) -> None:
        """处理接收到的飞书消息。

        Args:
            data: 飞书事件数据（P2ImMessageReceiveV1）
        """
        try:
            # 解析消息
            message = FeishuMessage.from_feishu_event(data)

            if not message.message_id:
                if self.logger:
                    self.logger.warning("Received message with no message_id")
                return

            # 忽略机器人自己发送的消息
            if message.sender_type == "bot":
                return

            if self.logger:
                self.logger.info(
                    "Received message: id=%s, chat_id=%s, type=%s, sender=%s",
                    message.message_id,
                    message.chat_id,
                    message.msg_type,
                    message.sender_id,
                )

            # 更新会话记录
            await self._update_session(message)

            # 提取文本内容
            text_content = message.get_text_content()

            # 发布到消息总线（如果可用）
            await self._publish_to_bus(message, text_content)

        except Exception as e:
            if self.logger:
                self.logger.exception("Failed to handle incoming message: %s", e)

    async def _update_session(self, message: FeishuMessage) -> None:
        """更新会话记录。"""
        session_key = f"{message.chat_id}:{message.sender_id}"
        now = time.time()

        async with self._lock:
            existing = self._sessions.get(session_key)
            if existing:
                existing.last_used_at = now
                existing.message_count += 1
                existing.last_message_type = message.msg_type
            else:
                self._sessions[session_key] = SessionRecord(
                    session_id=session_key,
                    chat_id=message.chat_id,
                    user_id=message.sender_id,
                    created_at=now,
                    last_used_at=now,
                    message_count=1,
                    last_message_type=message.msg_type,
                )

            # 持久化到 store
            if self.store:
                try:
                    record = self._sessions[session_key]
                    await self.store.set(
                        f"feishu_session:{session_key}",
                        record.to_dict(),
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.warning("Failed to persist session: %s", e)

    async def _publish_to_bus(
        self,
        message: FeishuMessage,
        text_content: str,
    ) -> None:
        """发布消息到消息总线。

        这里将飞书消息转换为 NEKO-1 内部格式，并发布到消息总线。
        消息总线接口：self.ctx.bus.publish(topic, payload)
        """
        # 构建内部消息格式
        internal_message = {
            "source": "feishu",
            "type": "message",
            "message_id": message.message_id,
            "chat_id": message.chat_id,
            "chat_type": message.chat_type,
            "user_id": message.sender_id,
            "content": text_content,
            "msg_type": message.msg_type,
            "raw_content": message.content,
            "timestamp": message.create_time,
            "parent_id": message.parent_id,
            "root_id": message.root_id,
        }

        if self.logger:
            self.logger.debug(
                "Publishing to bus: %s",
                json.dumps(internal_message, ensure_ascii=False)[:200],
            )

        # 发布到消息总线
        # 如果 ctx.bus 不可用，只记录日志
        if hasattr(self, "ctx") and hasattr(self.ctx, "bus"):
            try:
                await self.ctx.bus.publish("feishu.messages", internal_message)
                if self.logger:
                    self.logger.debug("Published to bus successfully")
            except Exception as e:
                if self.logger:
                    self.logger.warning("Failed to publish to bus: %s", e)
        else:
            if self.logger:
                self.logger.debug("Bus not available, message logged only")

    async def get_session(self, chat_id: str, user_id: str) -> Optional[SessionRecord]:
        """获取会话记录。"""
        session_key = f"{chat_id}:{user_id}"
        async with self._lock:
            return self._sessions.get(session_key)

    async def list_sessions(self) -> list[SessionRecord]:
        """列出所有会话。"""
        async with self._lock:
            records = list(self._sessions.values())
        records.sort(key=lambda r: r.last_used_at, reverse=True)
        return records

    async def clear_sessions(self) -> int:
        """清除所有会话。"""
        async with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            return count


__all__ = ["MessageHandler"]
