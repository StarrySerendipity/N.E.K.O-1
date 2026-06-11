"""
WeChat iLink Bot API client wrapper for the WeChat Neko Adapter plugin.

Handles QR code login, long-poll message receiving, and message sending
using the wechatbot Python SDK (https://www.wechatbot.dev/en/python).
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

try:
    import wechatbot
except ImportError:
    wechatbot = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class WeChatMessage:
    """Normalized WeChat message."""
    msg_id: str
    sender_id: str
    sender_name: str
    chat_id: str
    chat_name: str
    text: str
    is_group: bool
    is_mention: bool = False
    timestamp: float = field(default_factory=time.time)

    @property
    def dedup_key(self) -> str:
        """Deduplication key to prevent double-processing."""
        return hashlib.md5(
            f"{self.msg_id}:{self.sender_id}:{self.text[:100]}".encode()
        ).hexdigest()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class WeChatClient:
    """Async wrapper around the wechatbot SDK iLink protocol.

    Usage::

        client = WeChatClient(session_dir=Path("./data"))
        await client.start()
        client.on_message(callback)
        await client.run()
    """

    def __init__(
        self,
        *,
        session_dir: Path | None = None,
        poll_interval: float = 2.0,
    ) -> None:
        self._session_dir = session_dir
        self._poll_interval = poll_interval
        self._running = False
        self._bot: Any | None = None
        self._message_handlers: list[Callable[[WeChatMessage], Coroutine[Any, Any, None]]] = []
        self._seen_ids: set[str] = set()
        self._seen_max = 10_000

    # -- public API ----------------------------------------------------------

    async def start(self) -> None:
        """Initialise the underlying SDK bot.

        The wechatbot SDK handles QR login + session persistence internally.
        If a prior session exists it auto-recovers; otherwise a QR code is
        printed to stdout for scanning.
        """
        if wechatbot is None:
            raise RuntimeError(
                "wechatbot SDK is not installed. "
                "Run: pip install wechatbot"
            )

        bot_kwargs: dict[str, Any] = {}
        if self._session_dir is not None:
            self._session_dir.mkdir(parents=True, exist_ok=True)
            bot_kwargs["storage"] = str(self._session_dir)

        self._bot = wechatbot.WeChatBot(**bot_kwargs)
        await self._bot.login()
        self._running = True

    async def stop(self) -> None:
        """Stop the message poll loop."""
        self._running = False

    def on_message(
        self,
        handler: Callable[[WeChatMessage], Coroutine[Any, Any, None]],
    ) -> None:
        """Register an async message handler. Multiple handlers are supported."""
        self._message_handlers.append(handler)

    async def send_text(self, chat_id: str, text: str) -> None:
        """Send a text message to a user or group."""
        if self._bot is None:
            raise RuntimeError("Client not started")
        await self._bot.reply(
            type("_dummy", (), {"userId": chat_id, "text": text})(),
            text,
        )

    async def run(self) -> None:
        """Enter the long-poll message loop. Runs until stop() is called."""
        if self._bot is None:
            raise RuntimeError("Client not started")
        while self._running:
            try:
                messages = await self._bot.poll(timeout=5)
                for raw in messages:
                    msg = self._parse_message(raw)
                    if msg is None:
                        continue
                    # Dedup
                    if msg.dedup_key in self._seen_ids:
                        continue
                    self._seen_ids.add(msg.dedup_key)
                    if len(self._seen_ids) > self._seen_max:
                        # Keep only the latest half
                        seen_list = list(self._seen_ids)
                        self._seen_ids = set(seen_list[len(seen_list) // 2 :])
                    # Dispatch
                    for handler in self._message_handlers:
                        try:
                            await handler(msg)
                        except Exception:
                            # Handler errors should not break the poll loop
                            pass
            except asyncio.CancelledError:
                break
            except Exception:
                # Network / protocol errors — back off briefly then retry
                await asyncio.sleep(self._poll_interval)

    # -- internal ------------------------------------------------------------

    def _parse_message(self, raw: Any) -> WeChatMessage | None:
        """Convert a raw SDK message object to WeChatMessage."""
        try:
            msg_id = str(getattr(raw, "id", "") or getattr(raw, "msgId", ""))
            if not msg_id:
                return None

            sender_id = str(getattr(raw, "userId", "") or getattr(raw, "senderId", ""))
            sender_name = str(getattr(raw, "userName", "") or getattr(raw, "senderName", ""))
            chat_id = str(getattr(raw, "chatId", "") or getattr(raw, "roomId", "") or sender_id)
            chat_name = str(getattr(raw, "chatName", "") or getattr(raw, "roomName", ""))
            text = str(getattr(raw, "text", "") or "")
            is_group = bool(getattr(raw, "isGroup", False) or getattr(raw, "roomId", None))
            is_mention = bool(getattr(raw, "isMention", False) or getattr(raw, "isAt", False))

            # Auto-detect group from text pattern "@me" if SDK doesn't flag it
            if is_group and not is_mention and "@me" in text.lower():
                is_mention = True

            return WeChatMessage(
                msg_id=msg_id,
                sender_id=sender_id,
                sender_name=sender_name or sender_id,
                chat_id=chat_id,
                chat_name=chat_name or chat_id,
                text=text,
                is_group=is_group,
                is_mention=is_mention,
            )
        except Exception:
            return None
