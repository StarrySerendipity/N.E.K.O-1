"""
Normalizer: converts raw WeChat messages into prompt-friendly text
for N.E.K.O's LLM processing.
"""
from __future__ import annotations

from .client import WeChatMessage


class WeChatNormalizer:
    """Normalizes WeChat messages into human-readable text for the LLM."""

    def normalize(self, message: WeChatMessage) -> str:
        """Convert a WeChatMessage to a prompt-friendly string."""
        if message.is_group:
            return f"[微信群 {message.chat_name}] {message.user_name} @了{{LANLAN_NAME}}：{message.text}"
        return f"[微信私聊] {message.user_name} 说：{message.text}"

    def normalize_with_media(self, message: WeChatMessage) -> str:
        """Convert a WeChatMessage including media info."""
        base = self.normalize(message)
        extras = []
        if message.msg_type == "image":
            extras.append("[图片]")
        elif message.msg_type == "voice":
            extras.append("[语音]")
        elif message.msg_type == "file":
            extras.append("[文件]")
        elif message.msg_type == "video":
            extras.append("[视频]")
        if extras:
            return base + " " + " ".join(extras)
        return base
