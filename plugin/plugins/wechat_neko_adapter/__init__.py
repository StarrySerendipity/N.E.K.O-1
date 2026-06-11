"""
WeChat Neko Adapter — connects WeChat iLink Bot API to N.E.K.O's AI brain.

Architecture:
  WeChat User → iLink API → WeChatClient → push_message → N.E.K.O LLM
    → AI reply captured via message_plane → WeChatClient.send_text() → User

Features:
  - Private chat: all messages forwarded to AI
  - Group chat: only @mentions forwarded to AI
  - Message deduplication
  - Whitelist / blacklist for group control
  - Session auto-recovery
  - AI reply auto-routing back to WeChat
"""
from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from plugin.sdk.plugin import (
    NekoPluginBase,
    neko_plugin,
    plugin_entry,
    lifecycle,
    timer_interval,
    message,
    Ok,
    Err,
    SdkError,
)

from .client import WeChatClient, WeChatMessage
from .normalizer import WeChatNormalizer
from .serializer import WeChatSerializer


@neko_plugin
class WeChatAdapterPlugin(NekoPluginBase):
    """Adapter that bridges WeChat iLink Bot API with N.E.K.O's AI system."""

    def __init__(self, ctx: Any):
        super().__init__(ctx)
        self.logger = ctx.logger
        self._client: WeChatClient | None = None
        self._poll_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._normalizer = WeChatNormalizer()
        self._serializer = WeChatSerializer()

        # Session tracking: sender_id → (chat_id, sender_name) for reply routing
        self._sessions: Dict[str, Dict[str, str]] = {}
        self._sessions_lock = threading.Lock()

        # Pending replies: msg_id → chat_id (used for AI reply routing)
        self._pending_replies: Dict[str, str] = {}
        self._pending_lock = threading.Lock()

        # Config (loaded from config.json or defaults)
        self._config: Dict[str, Any] = {}

        # Auto-reply toggle: whether to send AI replies back to WeChat
        self._auto_reply = True

    # -- lifecycle -----------------------------------------------------------

    @lifecycle(id="startup")
    async def on_startup(self, **_) -> Ok | Err:
        """Load config and start the WeChat client."""
        self._load_config()
        self._auto_reply = bool(self._config.get("auto_reply", True))

        session_dir = self._config.get("session_dir", "")
        if session_dir:
            sd = Path(session_dir)
        else:
            sd = self.data_path("session")

        poll_interval = float(self._config.get("poll_interval", 2.0))

        try:
            self._client = WeChatClient(
                session_dir=sd,
                poll_interval=poll_interval,
            )
            await self._client.start()
            self._client.on_message(self._handle_wechat_message)
        except RuntimeError as e:
            return Err(SdkError(f"wechatbot SDK not available: {e}"))
        except Exception as e:
            return Err(SdkError(f"Failed to start WeChat client: {e}"))

        # Start the poll loop as a background task
        self._loop = asyncio.get_running_loop()
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
                "sender_id": {"type": "string", "description": "发送者 ID"},
                "sender_name": {"type": "string", "description": "发送者昵称"},
                "chat_id": {"type": "string", "description": "聊天 ID"},
                "is_group": {"type": "boolean", "description": "是否为群聊"},
                "is_mention": {"type": "boolean", "description": "是否被 @"},
            },
        },
    )
    async def handle_wechat_message_entry(
        self,
        text: str = "",
        sender_id: str = "",
        sender_name: str = "",
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

        if sender_id in self._config.get("blacklist", []):
            return Ok({"status": "ignored_blacklist"})

        with self._sessions_lock:
            self._sessions[sender_id] = {
                "chat_id": chat_id,
                "sender_name": sender_name,
                "chat_name": chat_name,
                "is_group": str(is_group),
            }

        await self._push_to_neko(
            text=text,
            sender_name=sender_name,
            is_group=is_group,
            chat_name=chat_name if is_group else "",
            sender_id=sender_id,
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
                "chat_id": {"type": "string", "description": "目标聊天 ID"},
                "text": {"type": "string", "description": "消息文本"},
            },
        },
    )
    async def send_message(self, chat_id: str = "", text: str = "", **_) -> Ok | Err:
        """Manually send a WeChat message."""
        if not chat_id or not text:
            return Err(SdkError("chat_id and text are required"))
        if self._client is None:
            return Err(SdkError("WeChat client not started"))
        try:
            await self._client.send_text(chat_id, text)
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

    # -- message handler (from main system) -----------------------------------

    @message(
        id="handle_ai_reply",
        source="agent_reply",
        auto_start=True,
    )
    async def handle_ai_reply(self, text: str = "", **_) -> Ok | Err:
        """Receive AI reply from the main system and route it back to WeChat.

        This is called when the LLM produces a response to a push_message
        that originated from this adapter.
        """
        if not self._auto_reply or not text:
            return Ok({"status": "skipped"})

        # Find the target chat_id from recent sessions
        chat_id = self._resolve_reply_target()
        if not chat_id:
            self.logger.debug("No reply target found for AI reply")
            return Ok({"status": "no_target"})

        if self._client is None:
            return Err(SdkError("WeChat client not started"))

        try:
            await self._client.send_text(chat_id, text)
            self.logger.info("AI reply sent to WeChat: {}", chat_id)
            return Ok({"status": "replied", "chat_id": chat_id})
        except Exception as e:
            return Err(SdkError(f"Failed to send reply: {e}"))

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
            "WeChat message: {} → {} [group={} mention={}]",
            message.sender_name,
            message.text[:50],
            message.is_group,
            message.is_mention,
        )

        # Group chat: only process @mentions
        if message.is_group:
            if not message.is_mention:
                return
            if not self._is_group_allowed(message.chat_id):
                return

        # Blacklist check
        if message.sender_id in self._config.get("blacklist", []):
            return

        # Track session
        with self._sessions_lock:
            self._sessions[message.sender_id] = {
                "chat_id": message.chat_id,
                "sender_name": message.sender_name,
                "chat_name": message.chat_name,
                "is_group": str(message.is_group),
            }

        # Track pending reply
        with self._pending_lock:
            self._pending_replies[message.msg_id] = message.chat_id

        # Push to N.E.K.O
        await self._push_to_neko(
            text=message.text,
            sender_name=message.sender_name,
            is_group=message.is_group,
            chat_name=message.chat_name if message.is_group else "",
            sender_id=message.sender_id,
            chat_id=message.chat_id,
            msg_id=message.msg_id,
        )

    async def _push_to_neko(
        self,
        *,
        text: str,
        sender_name: str,
        is_group: bool,
        chat_name: str,
        sender_id: str,
        chat_id: str,
        msg_id: str = "",
    ) -> None:
        """Push a WeChat message to N.E.K.O's AI system via push_message.

        Uses ai_behavior="respond" to trigger an immediate AI reply.
        """
        if is_group:
            parts_text = (
                f"[微信群 {chat_name}] {sender_name} @了{{LANLAN_NAME}}：{text}"
            )
        else:
            parts_text = f"[微信私聊] {sender_name} 说：{text}"

        self.push_message(
            parts=[{"type": "text", "text": parts_text}],
            ai_behavior="respond",
            source="wechat",
        )
        self.logger.info("Pushed WeChat message to N.E.K.O AI: {}", sender_name)

    def _resolve_reply_target(self) -> Optional[str]:
        """Find the most recent chat_id to reply to.

        Uses the last active private chat session.
        """
        with self._sessions_lock:
            if not self._sessions:
                return None
            # Return the most recently active non-group session
            for sid in reversed(list(self._sessions.keys())):
                info = self._sessions[sid]
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
