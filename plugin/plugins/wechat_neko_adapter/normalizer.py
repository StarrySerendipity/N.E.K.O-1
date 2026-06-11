"""
Normalizer: converts raw WeChat messages into GatewayRequest objects
that the Adapter Gateway Core can process.
"""
from __future__ import annotations

from typing import Any

from plugin.sdk.adapter.gateway_models import ExternalRequest, GatewayRequest
from .client import WeChatMessage


class WeChatNormalizer:
    """Normalizes WeChat messages into the adapter gateway request format."""

    def normalize(self, message: WeChatMessage) -> GatewayRequest:
        """Convert a WeChatMessage to a GatewayRequest."""
        external = ExternalRequest(
            protocol="wechat_ilink",
            raw={
                "msg_id": message.msg_id,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
                "chat_id": message.chat_id,
                "chat_name": message.chat_name,
                "text": message.text,
                "is_group": message.is_group,
                "is_mention": message.is_mention,
                "timestamp": message.timestamp,
            },
        )

        # Build a human-readable instruction for the LLM
        if message.is_group:
            context_prefix = (
                f"[群聊 {message.chat_name}] {message.sender_name} 说: "
            )
        else:
            context_prefix = (
                f"[私聊] {message.sender_name} 说: "
            )

        return GatewayRequest(
            external=external,
            plugin_id="wechat_neko_adapter",
            entry_id="wechat_message",
            args={
                "text": message.text,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
                "chat_id": message.chat_id,
                "chat_name": message.chat_name,
                "is_group": message.is_group,
                "is_mention": message.is_mention,
                "msg_id": message.msg_id,
                "_context": context_prefix + message.text,
            },
        )
