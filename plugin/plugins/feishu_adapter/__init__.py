"""Feishu Adapter Plugin

飞书/Lark 频道适配器，让猫娘通过飞书与用户交互。

功能：
- 接收飞书用户消息（文本、图片、文件等）
- 发送回复消息（文本、卡片、媒体）
- 支持 WebSocket 和 Webhook 两种连接模式
- 会话管理和状态持久化

设计参考：
- OpenClaw Feishu Plugin（extensions/feishu）
- N.E.K.O hermes_adapter / openclaw_adapter 的 Plugin 范式

飞书 SDK：lark-oapi（Python）
文档：https://open.feishu.cn/document/home/index
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from plugin.sdk.plugin import (
    NekoPluginBase,
    neko_plugin,
    plugin_entry,
    lifecycle,
    llm_tool,
    Ok,
    Err,
    SdkError,
)

from .models import AdapterConfig, FeishuMessage, SendMessageResult
from .errors import (
    ClassifiedError,
    is_retryable,
    classify_error,
    CONFIG_MISSING,
    AUTH_ERROR,
)
from .client import FeishuClient
from .message_handler import MessageHandler


# ---------------------------------------------------------------------------
# 插件主类
# ---------------------------------------------------------------------------


@neko_plugin
class FeishuAdapterPlugin(NekoPluginBase):
    """飞书频道适配器插件。

    通过飞书 SDK 将猫娘的能力暴露给飞书用户。
    用户可以在飞书中与猫娘交互，猫娘会自动回复。
    """

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.file_logger = self.enable_file_logging(log_level="INFO")
        self.logger = self.file_logger

        self._config: AdapterConfig = AdapterConfig()
        self._client: Optional[FeishuClient] = None
        self._message_handler: Optional[MessageHandler] = None
        self._ready: bool = False
        self._ws_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    @lifecycle(id="startup")
    async def startup(self, **_) -> Any:
        try:
            cfg_dict = await self._load_config_section("feishu")
            self._config = AdapterConfig.from_config_dict(cfg_dict)

            if not self.store.enabled:
                self.store.enabled = True
                self.logger.info("PluginStore auto-enabled for state persistence")

            self._client = FeishuClient(self._config, logger=self.logger)
            self._message_handler = MessageHandler(
                client=self._client,
                store=self.store,
                logger=self.logger,
                ctx=self.ctx,
            )

            self._ready = True
            configured = bool(self._config.app_id and self._config.app_secret)
            self.logger.info(
                "FeishuAdapter started: configured=%s app_id=%r connection_mode=%r",
                configured,
                self._config.app_id or "(empty)",
                self._config.connection_mode,
            )

            # 如果是 WebSocket 模式，启动 WebSocket 客户端
            if configured and self._config.connection_mode == "websocket":
                self._ws_task = asyncio.create_task(self._start_websocket())

            return Ok({
                "status": "ready",
                "configured": configured,
                "app_id": self._config.app_id or "",
                "connection_mode": self._config.connection_mode,
            })
        except Exception as e:
            self.logger.exception("FeishuAdapter startup failed")
            return Err(SdkError(f"startup failed: {e}"))

    @lifecycle(id="shutdown")
    async def shutdown(self, **_) -> Any:
        self._ready = False
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        self.logger.info("FeishuAdapter shutdown")
        return Ok({"status": "shutdown"})

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    async def _load_config_section(self, section: str) -> dict[str, Any]:
        try:
            cfg = await self.config.dump(timeout=5.0)
            if isinstance(cfg, dict):
                data = cfg.get(section)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            self.logger.warning("Failed to load config section %s: %s", section, e)
        return {}

    def _ensure_ready(self) -> Optional[Any]:
        if not self._ready:
            return Err(SdkError("Feishu Adapter not ready"))
        if self._client is None or self._message_handler is None:
            return Err(SdkError("Feishu Adapter internal state invalid"))
        return None

    # ------------------------------------------------------------------
    # WebSocket 模式
    # ------------------------------------------------------------------

    async def _start_websocket(self) -> None:
        """启动 WebSocket 连接（长轮询模式）。"""
        try:
            import lark_oapi as lark
            from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

            def _handle_message(data: P2ImMessageReceiveV1) -> None:
                """处理接收到的飞书消息。"""
                try:
                    asyncio.create_task(
                        self._message_handler.handle_incoming_message(data)
                    )
                except Exception as e:
                    self.logger.error("Failed to handle message: %s", e)

            # 创建事件处理器
            handler = (
                lark.EventDispatcherHandler.builder(
                    self._config.encrypt_key,
                    self._config.verification_token,
                )
                .register_p2_im_message_receive_v1(_handle_message)
                .build()
            )

            # 创建 WebSocket 客户端
            ws_client = (
                lark.ws.Client(
                    self._config.app_id,
                    self._config.app_secret,
                    event_handler=handler,
                    log_level=lark.LogLevel.DEBUG
                    if self._config.log_level == "DEBUG"
                    else lark.LogLevel.INFO,
                )
            )

            self.logger.info("Starting Feishu WebSocket client...")
            ws_client.start()

        except ImportError:
            self.logger.error(
                "lark-oapi not installed. Run: pip install lark-oapi"
            )
        except Exception as e:
            self.logger.exception("WebSocket client failed: %s", e)

    # ==================================================================
    # LLM 工具集
    # ==================================================================

    @llm_tool(
        name="feishu_send_message",
        description=(
            "通过飞书发送消息给用户。\n\n"
            "适用场景：\n"
            "- 主动通知用户\n"
            "- 回复用户消息\n"
            "- 发送卡片消息\n\n"
            "参数说明：\n"
            "- chat_id: 飞书群组或用户 ID。\n"
            "- content: 消息内容。\n"
            "- msg_type: 消息类型（text, interactive, post）。默认 text。\n\n"
            "返回：包含消息发送结果的字典。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "飞书群组或用户 ID。",
                },
                "content": {
                    "type": "string",
                    "description": "消息内容。",
                },
                "msg_type": {
                    "type": "string",
                    "description": "消息类型（text, interactive, post）。默认 text。",
                    "enum": ["text", "interactive", "post"],
                },
            },
            "required": ["chat_id", "content"],
        },
        timeout=30.0,
    )
    async def feishu_send_message(
        self,
        chat_id: str = "",
        content: str = "",
        msg_type: str = "text",
        **_,
    ) -> dict[str, Any]:
        """通过飞书发送消息。"""
        not_ready = self._ensure_ready()
        if not_ready is not None:
            return not_ready

        if not chat_id or not chat_id.strip():
            return Err(SdkError("chat_id 不能为空"))
        if not content or not content.strip():
            return Err(SdkError("content 不能为空"))

        try:
            assert self._client is not None
            result = await self._client.send_message(
                chat_id=chat_id,
                content=content,
                msg_type=msg_type,
            )
            return Ok(result.to_dict())
        except Exception as e:
            self.logger.exception("feishu_send_message failed")
            return Err(SdkError(f"发送消息失败: {e}"))

    @llm_tool(
        name="feishu_check_health",
        description="检查飞书适配器是否可用。返回连通性、配置状态等信息。",
        parameters={"type": "object", "properties": {}},
        timeout=10.0,
    )
    async def feishu_check_health(self, **_) -> dict[str, Any]:
        """检查飞书适配器健康状态。"""
        try:
            assert self._client is not None
            reachable, info = await self._client.check_health()
            return Ok({
                "configured": bool(self._config.app_id and self._config.app_secret),
                "reachable": reachable,
                "app_id": self._config.app_id or "",
                "connection_mode": self._config.connection_mode,
                "info": info,
                "ready": self._ready,
                "config": self._config.to_dict(),
            })
        except Exception as e:
            self.logger.exception("feishu_check_health failed")
            return Err(SdkError(f"健康检查失败: {e}"))

    @llm_tool(
        name="feishu_get_config",
        description="获取飞书适配器的当前配置。",
        parameters={"type": "object", "properties": {}},
        timeout=5.0,
    )
    async def feishu_get_config(self, **_) -> dict[str, Any]:
        """获取飞书适配器配置。"""
        try:
            return Ok({
                "config": self._config.to_dict(),
                "ready": self._ready,
            })
        except Exception as e:
            return Err(SdkError(f"获取配置失败: {e}"))

    # ==================================================================
    # 插件入口
    # ==================================================================

    @plugin_entry(
        id="send",
        name="发送飞书消息",
        description="通过飞书发送消息给用户。",
        llm_result_fields=["message_id", "chat_id"],
        input_schema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "飞书群组或用户 ID"},
                "content": {"type": "string", "description": "消息内容"},
                "msg_type": {
                    "type": "string",
                    "description": "消息类型",
                    "enum": ["text", "interactive", "post"],
                },
            },
            "required": ["chat_id", "content"],
        },
    )
    async def send_entry(
        self,
        chat_id: str = "",
        content: str = "",
        msg_type: str = "text",
        **_,
    ) -> Any:
        not_ready = self._ensure_ready()
        if not_ready is not None:
            return not_ready
        if not chat_id or not content:
            return Err(SdkError("chat_id 和 content 不能为空"))
        try:
            assert self._client is not None
            result = await self._client.send_message(
                chat_id=chat_id,
                content=content,
                msg_type=msg_type,
            )
            return Ok(result.to_dict())
        except Exception as e:
            self.logger.exception("send_entry failed")
            return Err(SdkError(f"发送消息失败: {e}"))


__all__ = ["FeishuAdapterPlugin"]
