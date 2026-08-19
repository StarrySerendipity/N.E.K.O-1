"""DeepSeek Harness Web API 插件

通过 HTTP API 直接与 DSH Web Server 通信，支持文本和图片。
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from plugin.sdk.plugin import (
    Err,
    NekoPluginBase,
    Ok,
    SdkError,
    lifecycle,
    llm_tool,
    neko_plugin,
    plugin_entry,
    ui,
)


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------


@dataclass
class DshWebConfig:
    """DSH Web API 配置"""
    host: str = "127.0.0.1"
    port: int = 3080
    workspace: str = ""
    timeout_sec: float = 300.0

    @classmethod
    def from_config_dict(cls, cfg: dict[str, Any]) -> "DshWebConfig":
        return cls(
            host=cfg.get("host", "127.0.0.1"),
            port=cfg.get("port", 3080),
            workspace=cfg.get("workspace", ""),
            timeout_sec=cfg.get("timeout_sec", 300.0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "workspace": self.workspace,
            "timeout_sec": self.timeout_sec,
        }

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


# ---------------------------------------------------------------------------
# DSH Web API 客户端
# ---------------------------------------------------------------------------


class DshWebClient:
    """DSH Web API 客户端"""

    def __init__(self, config: DshWebConfig, logger=None):
        self.config = config
        self.logger = logger
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout_sec),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _post_api(self, method: str, args: dict[str, Any]) -> dict[str, Any]:
        """调用 DSH API"""
        client = await self._get_client()

        payload = {
            "rpcId": str(uuid.uuid4()),
            "method": method,
            "args": args,
        }

        if self.logger:
            self.logger.info("DSH API call: {} args={}", method, list(args.keys()))

        response = await client.post(
            f"/api/{method}",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        result = response.json()

        if self.logger:
            self.logger.info("DSH API response: ok={}", result.get("result", {}).get("ok"))

        # 检查响应格式
        if result.get("type") == "server-response":
            inner = result.get("result", {})
            if not inner.get("ok"):
                error = inner.get("error", {})
                raise RuntimeError(f"DSH API error: {error.get('message', 'Unknown error')}")
            return inner.get("value", {})

        return result

    async def check_health(self) -> dict[str, Any]:
        """检查 DSH Web Server 是否可用"""
        try:
            client = await self._get_client()
            response = await client.get("/api/events.host", timeout=5.0)
            return {
                "available": True,
                "status_code": response.status_code,
                "message": "DSH Web Server 可用",
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "message": f"DSH Web Server 不可用: {e}",
            }

    async def list_sessions(self) -> dict[str, Any]:
        """列出所有会话"""
        return await self._post_api("session.list", {})

    async def create_session(self, name: Optional[str] = None) -> dict[str, Any]:
        """创建新会话"""
        args = {}
        if name:
            args["name"] = name
        return await self._post_api("session.create", args)

    async def send_prompt(
        self,
        session_id: str,
        content: str,
        images: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """发送消息给 DSH

        Args:
            session_id: 会话 ID
            content: 文本内容
            images: 图片列表，每项包含 {"attachmentId": "...", "mediaType": "image/png"}

        Returns:
            API 响应
        """
        # 构建内容块
        content_blocks = [{"type": "text", "text": content}]

        # 添加图片
        if images:
            for img in images:
                content_blocks.append({
                    "type": "image",
                    "attachment": {
                        "attachmentId": img["attachmentId"],
                        "mediaType": img.get("mediaType", "image/png"),
                    },
                })

        args = {
            "sessionId": session_id,
            "content": content_blocks,
        }

        return await self._post_api("session.prompt", args)

    async def get_history(self, session_id: str) -> dict[str, Any]:
        """获取会话历史"""
        return await self._post_api("session.history", {"sessionId": session_id})

    async def upload_attachment(
        self,
        session_id: str,
        file_path: str,
        media_type: str = "image/png",
    ) -> dict[str, Any]:
        """上传附件

        Args:
            session_id: 会话 ID
            file_path: 文件路径
            media_type: MIME 类型

        Returns:
            包含 attachmentId 的响应
        """
        client = await self._get_client()

        with open(file_path, "rb") as f:
            file_content = f.read()

        # 使用 multipart 上传
        files = {"file": (file_path, file_content, media_type)}
        data = {"sessionId": session_id}

        response = await client.post(
            "/api/session.attachment",
            files=files,
            data=data,
        )
        response.raise_for_status()

        return response.json()


# ---------------------------------------------------------------------------
# 插件主体
# ---------------------------------------------------------------------------


@neko_plugin
class DshWebPlugin(NekoPluginBase):
    """DeepSeek Harness Web API 插件"""

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.file_logger = self.enable_file_logging(log_level="INFO")
        self.logger = self.file_logger

        self._config: Optional[DshWebConfig] = None
        self._client: Optional[DshWebClient] = None

    # ----- 生命周期 -----

    @lifecycle(id="startup")
    async def startup(self) -> Optional[str]:
        """插件启动"""
        # 加载配置
        cfg_dict = self.ctx.get("config", {})
        self._config = DshWebConfig.from_config_dict(cfg_dict)

        # 创建客户端
        self._client = DshWebClient(self._config, logger=self.logger)

        # 检查 DSH Web Server 是否可用
        health = await self._client.check_health()
        if not health["available"]:
            self.logger.warning("DSH Web Server 不可用: {}", health["message"])
            return None  # 非阻塞，继续启动

        self.logger.info("DSH Web API 插件已启动，连接到 {}", self._config.base_url)
        return None

    @lifecycle(id="shutdown")
    async def shutdown(self) -> None:
        """插件关闭"""
        if self._client:
            await self._client.close()

    # ----- LLM 工具 -----

    @llm_tool(
        name="dsh_web_send",
        description=(
            "发送消息给 DeepSeek Harness。支持文本和图片。DSH 会执行任务并返回结果。\n\n"
            "适用场景：\n"
            "- 执行复杂编程任务\n"
            "- 分析代码项目\n"
            "- 发送图片进行分析\n"
            "- 任何需要 DeepSeek 能力的任务"
        ),
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "要发送的消息内容",
                },
                "session_id": {
                    "type": "string",
                    "description": "会话 ID（可选，不传则创建新会话）",
                },
                "image_path": {
                    "type": "string",
                    "description": "图片文件路径（可选，支持 png/jpg/gif/webp）",
                },
            },
            "required": ["prompt"],
        },
        timeout=300.0,
    )
    async def dsh_web_send(
        self,
        prompt: str = "",
        session_id: str = "",
        image_path: str = "",
        **_,
    ) -> dict[str, Any]:
        """发送消息给 DSH"""
        if not self._client:
            return {"error": "DSH Web 客户端未初始化"}

        if not prompt or not prompt.strip():
            return Err(SdkError("prompt 不能为空"))

        # 如果没有指定会话，创建一个新会话
        if not session_id:
            session_result = await self._client.create_session()
            session_id = session_result.get("sessionId") or session_result.get("id")
            if not session_id:
                return {"error": "无法创建会话"}

        # 处理图片上传
        images = None
        if image_path:
            import mimetypes
            media_type, _ = mimetypes.guess_type(image_path)
            if not media_type:
                media_type = "image/png"

            try:
                upload_result = await self._client.upload_attachment(
                    session_id, image_path, media_type
                )
                attachment_id = upload_result.get("attachmentId")
                if attachment_id:
                    images = [{"attachmentId": attachment_id, "mediaType": media_type}]
            except Exception as e:
                self.logger.warning("图片上传失败: {}", str(e))

        # 发送消息
        try:
            result = await self._client.send_prompt(session_id, prompt, images)

            return {
                "session_id": session_id,
                "result": result,
                "message": "消息已发送",
            }
        except Exception as e:
            return {
                "session_id": session_id,
                "error": str(e),
                "message": f"发送失败: {e}",
            }

    @llm_tool(
        name="dsh_web_status",
        description=(
            "检查 DeepSeek Harness Web Server 是否可用。\n\n"
            "适用场景：\n"
            "- 在调用 dsh_web_send 之前确认服务可用\n"
            "- 排查连接问题"
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        timeout=10.0,
    )
    async def dsh_web_status(self, **_) -> dict[str, Any]:
        """检查 DSH 状态"""
        if not self._client:
            return {
                "available": False,
                "message": "DSH Web 客户端未初始化",
                "config": self._config.to_dict() if self._config else {},
            }

        health = await self._client.check_health()

        return {
            **health,
            "config": self._config.to_dict(),
        }

    @llm_tool(
        name="dsh_web_sessions",
        description="列出所有 DeepSeek Harness 会话。",
        parameters={
            "type": "object",
            "properties": {},
        },
        timeout=30.0,
    )
    async def dsh_web_sessions(self, **_) -> dict[str, Any]:
        """列出所有会话"""
        if not self._client:
            return {"error": "DSH Web 客户端未初始化"}

        try:
            result = await self._client.list_sessions()
            return {
                "sessions": result,
                "message": "会话列表已获取",
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": f"获取会话列表失败: {e}",
            }

    @llm_tool(
        name="dsh_web_create_session",
        description="创建一个新的 DeepSeek Harness 会话。",
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "会话名称（可选）",
                },
            },
        },
        timeout=30.0,
    )
    async def dsh_web_create_session(
        self,
        name: str = "",
        **_,
    ) -> dict[str, Any]:
        """创建新会话"""
        if not self._client:
            return {"error": "DSH Web 客户端未初始化"}

        try:
            result = await self._client.create_session(name if name else None)
            return {
                "session": result,
                "message": "会话已创建",
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": f"创建会话失败: {e}",
            }
