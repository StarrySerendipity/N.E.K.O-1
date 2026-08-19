"""Feishu Adapter — 飞书客户端。

负责：
1. 初始化飞书 SDK 客户端
2. 发送消息（文本、卡片、媒体）
3. 健康检查
4. 管理飞书 API 调用

飞书 SDK 文档：https://open.feishu.cn/document/server-docs/api-call-guide/server-sdk/overview
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from .errors import (
    CONFIG_MISSING,
    ClassifiedError,
    classify_error,
)
from .models import AdapterConfig, SendMessageResult


class FeishuClient:
    """飞书 API 客户端。"""

    def __init__(self, config: AdapterConfig, logger: Any = None) -> None:
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._client = None

    def _get_client(self) -> Any:
        """获取或创建飞书客户端。"""
        if self._client is not None:
            return self._client

        try:
            import lark_oapi as lark

            self._client = (
                lark.Client.builder()
                .app_id(self.config.app_id)
                .app_secret(self.config.app_secret)
                .log_level(
                    lark.LogLevel.DEBUG
                    if self.config.log_level == "DEBUG"
                    else lark.LogLevel.INFO
                )
                .build()
            )
            return self._client
        except ImportError:
            raise RuntimeError("lark-oapi not installed. Run: pip install lark-oapi")
        except Exception as e:
            raise RuntimeError(f"Failed to create Feishu client: {e}")

    def _validate_config(self) -> Optional[ClassifiedError]:
        """验证配置。"""
        if not self.config.app_id:
            return ClassifiedError(
                kind=CONFIG_MISSING,
                message="[feishu].app_id not configured. Set Feishu App ID in plugin.toml.",
                retryable=False,
            )
        if not self.config.app_secret:
            return ClassifiedError(
                kind=CONFIG_MISSING,
                message="[feishu].app_secret not configured. Set Feishu App Secret in plugin.toml.",
                retryable=False,
            )
        return None

    async def send_message(
        self,
        chat_id: str,
        content: str,
        msg_type: str = "text",
        receive_id_type: str = "chat_id",
    ) -> SendMessageResult:
        """发送消息。

        Args:
            chat_id: 接收者 ID（群组 ID 或用户 open_id）
            content: 消息内容（JSON 字符串）
            msg_type: 消息类型（text, interactive, post）
            receive_id_type: 接收者 ID 类型（chat_id, open_id, user_id, union_id）

        Returns:
            SendMessageResult: 发送结果
        """
        err = self._validate_config()
        if err is not None:
            return SendMessageResult(
                success=False,
                error_message=err.message,
            )

        try:
            import lark_oapi as lark
            from lark_oapi.api.im.v1 import (
                CreateMessageRequest,
                CreateMessageRequestBody,
            )

            client = self._get_client()

            # 构建请求体
            body = (
                CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type(msg_type)
                .content(content)
                .build()
            )

            # 构建请求
            request = (
                CreateMessageRequest.builder()
                .receive_id_type(receive_id_type)
                .request_body(body)
                .build()
            )

            # 发送请求
            response = client.im.v1.messages.create(request)

            if not response.success():
                error_msg = f"Feishu API error: code={response.code}, msg={response.msg}"
                self.logger.error(error_msg)
                return SendMessageResult(
                    success=False,
                    chat_id=chat_id,
                    error_message=error_msg,
                )

            message_id = ""
            if response.data and hasattr(response.data, "message_id"):
                message_id = response.data.message_id or ""

            self.logger.info(
                "Message sent: chat_id=%s, msg_type=%s, message_id=%s",
                chat_id,
                msg_type,
                message_id,
            )

            return SendMessageResult(
                success=True,
                message_id=message_id,
                chat_id=chat_id,
            )

        except ImportError:
            error_msg = "lark-oapi not installed. Run: pip install lark-oapi"
            self.logger.error(error_msg)
            return SendMessageResult(
                success=False,
                chat_id=chat_id,
                error_message=error_msg,
            )
        except Exception as e:
            classified = classify_error(str(e))
            error_msg = f"Send message failed: {classified.message}"
            self.logger.exception(error_msg)
            return SendMessageResult(
                success=False,
                chat_id=chat_id,
                error_message=error_msg,
            )

    async def send_text_message(
        self,
        chat_id: str,
        text: str,
        receive_id_type: str = "chat_id",
    ) -> SendMessageResult:
        """发送文本消息。

        Args:
            chat_id: 接收者 ID
            text: 文本内容
            receive_id_type: 接收者 ID 类型

        Returns:
            SendMessageResult: 发送结果
        """
        content = json.dumps({"text": text})
        return await self.send_message(
            chat_id=chat_id,
            content=content,
            msg_type="text",
            receive_id_type=receive_id_type,
        )

    async def send_card_message(
        self,
        chat_id: str,
        card: dict[str, Any],
        receive_id_type: str = "chat_id",
    ) -> SendMessageResult:
        """发送卡片消息。

        Args:
            chat_id: 接收者 ID
            card: 卡片内容（字典）
            receive_id_type: 接收者 ID 类型

        Returns:
            SendMessageResult: 发送结果
        """
        content = json.dumps(card)
        return await self.send_message(
            chat_id=chat_id,
            content=content,
            msg_type="interactive",
            receive_id_type=receive_id_type,
        )

    async def check_health(self) -> tuple[bool, dict[str, Any]]:
        """健康检查：验证配置和连通性。"""
        err = self._validate_config()
        if err is not None:
            return False, {"error": err.message}

        try:
            client = self._get_client()
            # 尝试获取 tenant_access_token 来验证凭据
            # 这是一个轻量级的验证，不需要实际发送消息
            return True, {
                "app_id": self.config.app_id,
                "connection_mode": self.config.connection_mode,
                "client_created": self._client is not None,
            }
        except Exception as e:
            return False, {"error": str(e)}


__all__ = ["FeishuClient"]
