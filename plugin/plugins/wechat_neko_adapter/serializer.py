"""
Serializer: converts N.E.K.O AI responses back into WeChat message format
for sending via the wechatbot SDK.
"""
from __future__ import annotations

from typing import Any


class WeChatSerializer:
    """Serializes GatewayResponse back to WeChat-compatible output."""

    def serialize(self, result: Any, *, chat_id: str) -> dict[str, Any]:
        """Prepare the response for sending to WeChat.

        Returns a dict with the text to send and the target chat_id.
        """
        text = self._extract_text(result)
        return {
            "chat_id": chat_id,
            "text": text,
        }

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Extract the reply text from various result shapes."""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            # Try common keys in order of preference
            for key in ("text", "content", "message", "reply", "summary"):
                if key in result:
                    val = result[key]
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            # Fallback: JSON dump
            import json
            return json.dumps(result, ensure_ascii=False, default=str)
        if result is None:
            return ""
        return str(result)
