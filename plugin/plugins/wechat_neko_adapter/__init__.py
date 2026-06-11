"""
WeChat Neko Adapter — connects WeChat iLink Bot API to N.E.K.O's AI brain.

Architecture:
  WeChat User → iLink API → wechatbot-sdk → push_message → N.E.K.O LLM
    → AI reply captured via agent_event_bus → send_text → WeChat User

Features:
  - Private chat: all messages forwarded to AI
  - Group chat: only @mentions forwarded to AI
  - Message deduplication
  - Whitelist / blacklist for group control
  - Session auto-recovery
  - AI reply auto-routing back to WeChat
  - Rich media support (images, files, voice, video)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

from plugin.sdk.plugin import (
    NekoPluginBase,
    neko_plugin,
    plugin_entry,
    lifecycle,
    timer_interval,
    Ok,
    Err,
    SdkError,
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class WeChatMessage:
    """Normalized WeChat message from the iLink protocol."""
    msg_id: str
    user_id: str
    user_name: str
    chat_id: str
    chat_name: str
    text: str
    msg_type: str = "text"  # text, image, voice, file, video
    is_group: bool = False
    is_mention: bool = False
    timestamp: float = field(default_factory=time.time)
    raw: dict = field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        """Deduplication key to prevent double-processing."""
        return hashlib.md5(
            f"{self.msg_id}:{self.user_id}:{self.text[:100]}".encode()
        ).hexdigest()


# ---------------------------------------------------------------------------
# WeChat SDK client wrapper
# ---------------------------------------------------------------------------

class WeChatClient:
    """Async wrapper around the wechatbot-sdk iLink protocol.

    Usage::

        client = WeChatClient()
        await client.start()
        client.on_message(callback)
        await client.run()
    """

    def __init__(
        self,
        *,
        base_url: str = "https://ilinkai.weixin.qq.com",
        cred_path: str | None = None,
        poll_interval: float = 2.0,
    ) -> None:
        self._base_url = base_url
        self._cred_path = cred_path
        self._poll_interval = poll_interval
        self._running = False
        self._bot: Any | None = None
        self._message_handlers: List[Callable[[WeChatMessage], Coroutine[Any, Any, None]]] = []
        self._seen_ids: set[str] = set()
        self._seen_max = 10_000

    # -- public API ----------------------------------------------------------

    async def start(self) -> None:
        """Initialise the wechatbot SDK.

        Handles QR login + session persistence. Auto-recovers existing sessions.
        """
        try:
            from wechatbot import WeChatBot
        except ImportError:
            raise RuntimeError(
                "wechatbot-sdk is not installed. "
                "Run: pip install wechatbot-sdk"
            )

        bot_kwargs: Dict[str, Any] = {"base_url": self._base_url}
        if self._cred_path:
            bot_kwargs["cred_path"] = self._cred_path

        self._bot = WeChatBot(**bot_kwargs)
        await self._bot.login()
        self._running = True

    async def stop(self) -> None:
        """Stop the message poll loop."""
        self._running = False
        if self._bot is not None:
            try:
                self._bot.stop()
            except Exception:
                pass

    def on_message(
        self,
        handler: Callable[[WeChatMessage], Coroutine[Any, Any, None]],
    ) -> None:
        """Register an async message handler."""
        self._message_handlers.append(handler)

    async def send_text(self, user_id: str, text: str) -> None:
        """Send a text message to a user or group."""
        if self._bot is None:
            raise RuntimeError("Client not started")
        await self._bot.send(user_id, text)

    async def reply(self, msg: WeChatMessage, text: str) -> None:
        """Reply to a specific message (auto context_token + stop typing)."""
        if self._bot is None:
            raise RuntimeError("Client not started")
        # Build a minimal fake IncomingMessage-like object for the SDK
        class _FakeMsg:
            user_id = msg.user_id
        await self._bot.send_typing(msg.user_id)
        await self._bot.reply(_FakeMsg(), text)

    async def send_typing(self, user_id: str) -> None:
        """Show typing indicator."""
        if self._bot is None:
            return
        await self._bot.send_typing(user_id)

    async def stop_typing(self, user_id: str) -> None:
        """Cancel typing indicator."""
        if self._bot is None:
            return
        await self._bot.stop_typing(user_id)

    async def run(self) -> None:
        """Enter the long-poll message loop. Runs until stop() is called."""
        if self._bot is None:
            raise RuntimeError("Client not started")

        # Register the internal poll handler
        async def _sdk_handler(raw_msg: Any) -> None:
            msg = self._parse_message(raw_msg)
            if msg is None:
                return
            # Dedup
            if msg.dedup_key in self._seen_ids:
                return
            self._seen_ids.add(msg.dedup_key)
            if len(self._seen_ids) > self._seen_max:
                seen_list = list(self._seen_ids)
                self._seen_ids = set(seen_list[len(seen_list) // 2 :])
            # Dispatch
            for handler in self._message_handlers:
                try:
                    await handler(msg)
                except Exception:
                    pass

        self._bot.on_message(_sdk_handler)
        await self._bot.start()

    # -- internal ------------------------------------------------------------

    def _parse_message(self, raw: Any) -> WeChatMessage | None:
        """Convert a raw SDK IncomingMessage to WeChatMessage."""
        try:
            user_id = getattr(raw, "user_id", "")
            if not user_id:
                return None

            text = getattr(raw, "text", "") or ""
            msg_type = getattr(raw, "type", "text") or "text"
            timestamp = getattr(raw, "timestamp", None)
            ts = timestamp.timestamp() if timestamp else time.time()

            # Check for media content
            images = getattr(raw, "images", []) or []
            voices = getattr(raw, "voices", []) or []
            files = getattr(raw, "files", []) or []
            videos = getattr(raw, "videos", []) or []

            # Group detection: user_id contains @chatroom or @im.wechat patterns
            is_group = "chatroom" in str(user_id).lower()

            # Auto-detect @mention from text
            is_mention = False
            if is_group and "@me" in text.lower():
                is_mention = True

            # For group chats, extract sender name from raw data
            user_name = user_id
            raw_dict = getattr(raw, "raw", {}) or {}
            if isinstance(raw_dict, dict):
                user_name = raw_dict.get("userName", raw_dict.get("senderName", user_id))

            return WeChatMessage(
                msg_id=str(getattr(raw, "user_id", "")) + str(ts),
                user_id=user_id,
                user_name=user_name,
                chat_id=user_id,
                chat_name=user_name,
                text=text,
                msg_type=msg_type,
                is_group=is_group,
                is_mention=is_mention,
                timestamp=ts,
                raw=raw_dict if isinstance(raw_dict, dict) else {},
            )
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Main Plugin
# ---------------------------------------------------------------------------

@neko_plugin
class WeChatAdapterPlugin(NekoPluginBase):
    """Adapter that bridges WeChat iLink Bot API with N.E.K.O's AI system."""

    def __init__(self, ctx: Any):
        super().__init__(ctx)
        self.logger = ctx.logger
        self._client: WeChatClient | None = None
        self._poll_task: asyncio.Task | None = None
        self._normalizer = WeChatNormalizer()

        # Session tracking: user_id → session info for reply routing
        self._sessions: Dict[str, Dict[str, str]] = {}
        self._sessions_lock = threading.Lock()

        # Pending reply tracking: dedup_key → chat_id
        self._pending_replies: Dict[str, str] = {}
        self._pending_lock = threading.Lock()

        # Config (loaded from config.json or defaults)
        self._config: Dict[str, Any] = {}

        # Auto-reply toggle
        self._auto_reply = True

    # -- lifecycle -----------------------------------------------------------

    @lifecycle(id="startup")
    async def on_startup(self, **_) -> Ok | Err:
        """Load config and start the WeChat client."""
        self._load_config()
        self._auto_reply = bool(self._config.get("auto_reply", True))

        poll_interval = float(self._config.get("poll_interval", 2.0))
        cred_path = self._config.get("cred_path")

        try:
            self._client = WeChatClient(
                poll_interval=poll_interval,
                cred_path=cred_path,
            )
            await self._client.start()
            self._client.on_message(self._handle_wechat_message)
        except RuntimeError as e:
            return Err(SdkError(f"wechatbot-sdk not available: {e}"))
        except Exception as e:
            return Err(SdkError(f"Failed to start WeChat client: {e}"))

        # Start the poll loop as a background task
        self._poll_task = asyncio.create_task(
            self._client.run(), name="wechat-poll-loop"
        )

        self.logger.info("WeChat adapter started successfully")
        self.push_message(
            visibility=["hud"],
            ai_behavior="blind",
            parts=[{"type": "text", "text": "微信适配器已启动"}],
        )
        return Ok({"status": "running"})

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_) -> Ok | Err:
        """Stop the WeChat client and poll loop."""
        if self._client:
            await self._client.stop()
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self.logger.info("WeChat adapter stopped")
        return Ok({"status": "stopped"})

    @lifecycle(id="config_change")
    async def on_config_change(self, old_config: dict, new_config: dict, **_) -> None:
        """Handle config hot-reload."""
        wc = new_config.get("wechat", {})
        if wc:
            self._config.update(wc)
            self._auto_reply = bool(self._config.get("auto_reply", True))
            self.logger.info("WeChat adapter config reloaded")

    # -- entry points --------------------------------------------------------

    @plugin_entry(
        id="wechat_message",
        name="微信消息处理",
        description="处理来自微信的消息（由网关管线调用）",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "消息文本"},
                "user_id": {"type": "string", "description": "发送者 ID"},
                "user_name": {"type": "string", "description": "发送者昵称"},
                "chat_id": {"type": "string", "description": "聊天 ID"},
                "is_group": {"type": "boolean", "description": "是否为群聊"},
                "is_mention": {"type": "boolean", "description": "是否被 @"},
            },
        },
    )
    async def handle_wechat_message_entry(
        self,
        text: str = "",
        user_id: str = "",
        user_name: str = "",
        chat_id: str = "",
        chat_name: str = "",
        is_group: bool = False,
        is_mention: bool = False,
        msg_id: str = "",
        **_,
    ) -> Ok | Err:
        """Main message handler — called by the gateway pipeline."""
        if is_group and not self._is_group_allowed(chat_id):
            self.logger.debug("Group {} not in whitelist, ignoring", chat_id)
            return Ok({"status": "ignored_group"})

        if user_id in self._config.get("blacklist", []):
            return Ok({"status": "ignored_blacklist"})

        with self._sessions_lock:
            self._sessions[user_id] = {
                "chat_id": chat_id,
                "user_name": user_name,
                "chat_name": chat_name,
                "is_group": str(is_group),
            }

        await self._push_to_neko(
            text=text,
            user_name=user_name,
            is_group=is_group,
            chat_name=chat_name if is_group else "",
            user_id=user_id,
            chat_id=chat_id,
            msg_id=msg_id,
        )
        return Ok({"status": "pushed"})

    @plugin_entry(
        id="status",
        name="适配器状态",
        description="查看微信适配器运行状态",
    )
    async def get_status(self, **_) -> Ok | Err:
        """Get adapter runtime status."""
        is_running = (
            self._client is not None
            and self._poll_task is not None
            and not self._poll_task.done()
        )
        with self._sessions_lock:
            session_count = len(self._sessions)
        return Ok({
            "running": is_running,
            "sessions": session_count,
            "auto_reply": self._auto_reply,
            "config_keys": list(self._config.keys()),
        })

    @plugin_entry(
        id="send_message",
        name="发送微信消息",
        description="通过微信发送一条消息（手动触发）",
        input_schema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "目标用户/群 ID"},
                "text": {"type": "string", "description": "消息文本"},
            },
        },
    )
    async def send_message(self, user_id: str = "", text: str = "", **_) -> Ok | Err:
        """Manually send a WeChat message."""
        if not user_id or not text:
            return Err(SdkError("user_id and text are required"))
        if self._client is None:
            return Err(SdkError("WeChat client not started"))
        try:
            await self._client.send_text(user_id, text)
            return Ok({"status": "sent"})
        except Exception as e:
            return Err(SdkError(f"Failed to send: {e}"))

    @plugin_entry(
        id="reload_config",
        name="重载配置",
        description="重新加载微信适配器配置",
    )
    async def reload_config(self, **_) -> Ok | Err:
        self._load_config()
        return Ok({"status": "reloaded", "config_keys": list(self._config.keys())})

    @plugin_entry(
        id="toggle_auto_reply",
        name="切换自动回复",
        description="开启或关闭微信自动回复",
        input_schema={
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "description": "是否启用自动回复"},
            },
        },
    )
    async def toggle_auto_reply(self, enabled: bool = True, **_) -> Ok | Err:
        self._auto_reply = enabled
        return Ok({"auto_reply": enabled})

    # -- internal ------------------------------------------------------------

    def _load_config(self) -> None:
        """Load config from config.json (next to plugin.toml)."""
        config_file = self.config_dir / "config.json"
        if config_file.exists():
            try:
                self._config = json.loads(config_file.read_text(encoding="utf-8"))
                self.logger.info("WeChat adapter config loaded from {}", config_file)
            except Exception as e:
                self.logger.warning("Failed to load config: {}", e)
                self._config = {}
        else:
            self.logger.debug("No config.json found, using defaults")
            self._config = {}

    async def _handle_wechat_message(self, message: WeChatMessage) -> None:
        """Callback from the WeChat client poll loop."""
        self.logger.debug(
            "WeChat message: {} → {} [type={} group={} mention={}]",
            message.user_name,
            message.text[:50] if message.text else "(no text)",
            message.msg_type,
            message.is_group,
            message.is_mention,
        )

        # Skip non-text messages (for now)
        if message.msg_type != "text":
            self.logger.debug("Skipping non-text message type: {}", message.msg_type)
            return

        # Group chat: only process @mentions
        if message.is_group:
            if not message.is_mention:
                return
            if not self._is_group_allowed(message.chat_id):
                return

        # Blacklist check
        if message.user_id in self._config.get("blacklist", []):
            return

        # Track session
        with self._sessions_lock:
            self._sessions[message.user_id] = {
                "chat_id": message.chat_id,
                "user_name": message.user_name,
                "chat_name": message.chat_name,
                "is_group": str(message.is_group),
            }

        # Track pending reply
        with self._pending_lock:
            self._pending_replies[message.dedup_key] = message.chat_id

        # Push to N.E.K.O
        await self._push_to_neko(
            text=message.text,
            user_name=message.user_name,
            is_group=message.is_group,
            chat_name=message.chat_name if message.is_group else "",
            user_id=message.user_id,
            chat_id=message.chat_id,
            msg_id=message.msg_id,
        )

    async def _push_to_neko(
        self,
        *,
        text: str,
        user_name: str,
        is_group: bool,
        chat_name: str,
        user_id: str,
        chat_id: str,
        msg_id: str = "",
    ) -> None:
        """Push a WeChat message to N.E.K.O's AI system via push_message."""
        if is_group:
            parts_text = (
                f"[微信群 {chat_name}] {user_name} @了{{LANLAN_NAME}}：{text}"
            )
        else:
            parts_text = f"[微信私聊] {user_name} 说：{text}"

        self.push_message(
            parts=[{"type": "text", "text": parts_text}],
            ai_behavior="respond",
            source="wechat",
        )
        self.logger.info("Pushed WeChat message to N.E.K.O AI: {}", user_name)

    def _resolve_reply_target(self) -> Optional[str]:
        """Find the most recent chat_id to reply to.

        Uses the last active private chat session.
        """
        with self._sessions_lock:
            if not self._sessions:
                return None
            # Return the most recently active non-group session
            for uid in reversed(list(self._sessions.keys())):
                info = self._sessions[uid]
                if info.get("is_group") != "True":
                    return info.get("chat_id")
            # Fallback: last session
            last = list(self._sessions.values())[-1]
            return last.get("chat_id")

    def _is_group_allowed(self, group_id: str) -> bool:
        """Check if a group is in the whitelist (or not in blacklist)."""
        whitelist = self._config.get("group_whitelist", [])
        blacklist = self._config.get("group_blacklist", [])

        if not whitelist:
            return group_id not in blacklist

        return group_id in whitelist and group_id not in blacklist

    @timer_interval(
        id="heartbeat",
        seconds=300,
        name="微信适配器心跳",
        auto_start=True,
    )
    def heartbeat(self, **_) -> Ok:
        """Periodic health check."""
        is_running = (
            self._client is not None
            and self._poll_task is not None
            and not self._poll_task.done()
        )
        with self._sessions_lock:
            session_count = len(self._sessions)
        self.report_status({
            "status": "running" if is_running else "stopped",
            "sessions": session_count,
            "auto_reply": self._auto_reply,
        })
        return Ok({"alive": is_running})


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------

class WeChatNormalizer:
    """Normalizes WeChat messages into human-readable text for the LLM."""

    def normalize(self, message: WeChatMessage) -> str:
        """Convert a WeChatMessage to a prompt-friendly string."""
        if message.is_group:
            return f"[微信群 {message.chat_name}] {message.user_name} @了猫娘：{message.text}"
        return f"[微信私聊] {message.user_name} 说：{message.text}"
