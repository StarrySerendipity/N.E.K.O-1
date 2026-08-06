"""
猫娘邮件插件 v0.1 (Neko Mail)

让猫娘能读取主人的 QQ 邮箱,生成邮件摘要、判断优先级、
帮主人标记已读、发送邮件。

数据模型:
  - EmailMessage: 完整邮件
  - EmailSummary: 今日摘要(按优先级分类)
  - EmailSnippet: 邮件摘要片段

LLM 工具:
  - neko_mail_get_summary: 获取今日邮件摘要
  - neko_mail_get_unread: 获取未读邮件列表
  - neko_mail_search: 搜索邮件
  - neko_mail_mark_read: 标记邮件已读
  - neko_mail_send: 发送邮件
  - neko_mail_list_folders: 列出邮箱文件夹
"""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Optional
from pathlib import Path

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

from .plugin import NekoMailPlugin

# ── 常量 ──────────────────────────────────────────────────────────────

_PLUGIN_ID = "neko_mail"
_DEFAULT_IMAP_SERVER = "imap.qq.com"
_DEFAULT_IMAP_PORT = 993
_DEFAULT_SMTP_SERVER = "smtp.qq.com"
_DEFAULT_SMTP_PORT = 465


# ── 插件主类 ──────────────────────────────────────────────────────────

@neko_plugin
class NekoMailPluginEntry(NekoPluginBase):
    """猫娘邮件插件 - N.E.K.O 插件入口"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.file_logger = self.enable_file_logging(log_level="INFO")
        self.logger = self.file_logger
        self._lock = threading.Lock()
        self._mail_plugin: Optional[NekoMailPlugin] = None

    # ── lifecycle ────────────────────────────────────────────────────

    @lifecycle(id="startup")
    async def startup(self, **_):
        """启动插件,加载配置"""
        cfg = await self.config.dump(timeout=5.0)
        cfg = cfg if isinstance(cfg, dict) else {}
        section = cfg.get("neko_mail") if isinstance(cfg.get("neko_mail"), dict) else {}

        # 读取配置
        email_addr = str(section.get("email_addr", "")).strip()
        auth_code = str(section.get("auth_code", "")).strip()
        imap_server = str(section.get("imap_server", _DEFAULT_IMAP_SERVER)).strip()
        imap_port = int(section.get("imap_port", _DEFAULT_IMAP_PORT))
        smtp_server = str(section.get("smtp_server", _DEFAULT_SMTP_SERVER)).strip()
        smtp_port = int(section.get("smtp_port", _DEFAULT_SMTP_PORT))

        # 高优先级发件人
        high_senders_raw = str(section.get("high_priority_senders", "")).strip()
        high_priority_senders = [s.strip() for s in high_senders_raw.split(",") if s.strip()] if high_senders_raw else []

        # 忽略的文件夹
        ignore_raw = str(section.get("ignore_folders", "")).strip()
        ignore_folders = [s.strip() for s in ignore_raw.split(",") if s.strip()] if ignore_raw else []

        if not email_addr or not auth_code:
            self.logger.error("QQ_EMAIL or QQ_AUTH_CODE not configured")
            return Err(SdkError("邮箱配置缺失: 请在 plugin.toml 中配置 neko_mail.email_addr 和 neko_mail.auth_code"))

        try:
            self._mail_plugin = NekoMailPlugin(
                email_addr=email_addr,
                auth_code=auth_code,
                imap_server=imap_server,
                imap_port=imap_port,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                high_priority_senders=high_priority_senders,
                ignore_folders=ignore_folders,
            )
        except Exception as e:
            self.logger.error("初始化邮件插件失败: {}", e)
            return Err(SdkError(f"初始化邮件插件失败: {e}"))

        self.logger.info(
            "NekoMail started: email={}, imap={}:{}, smtp={}:{}",
            email_addr, imap_server, imap_port, smtp_server, smtp_port,
        )
        return Ok({"status": "running", "version": "0.1.0", "email": email_addr})

    @lifecycle(id="shutdown")
    def shutdown(self, **_):
        """关闭插件"""
        if self._mail_plugin:
            self._mail_plugin.close()
        self.logger.info("NekoMail shutdown")
        return Ok({"status": "shutdown"})

    # ── 辅助方法 ─────────────────────────────────────────────────────

    def _get_plugin(self) -> NekoMailPlugin:
        """获取邮件插件实例"""
        if self._mail_plugin is None:
            raise RuntimeError("邮件插件未初始化,请检查配置")
        return self._mail_plugin

    # ── LLM 工具 ─────────────────────────────────────────────────────

    @llm_tool(
        name="neko_mail_get_summary",
        description="获取今日邮件摘要。返回未读数、今日邮件数、按优先级分类的邮件列表。猫娘可以用这个信息告诉主人今天有哪些重要邮件。",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        timeout=30.0,
    )
    @plugin_entry(
        id="get_summary",
        name="获取今日邮件摘要",
        description="获取今日邮件摘要,按优先级分类",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        llm_result_fields=["total_unread", "total_today", "high_priority", "medium_priority", "low_priority", "catgirl_text"],
    )
    async def get_summary(self, **_):
        """获取今日邮件摘要"""
        try:
            plugin = self._get_plugin()
            result = plugin.get_today_summary()
            if "error" in result:
                return Err(SdkError(result["error"]))
            return Ok(result)
        except Exception as e:
            return Err(SdkError(f"获取邮件摘要失败: {e}"))

    @llm_tool(
        name="neko_mail_get_unread",
        description="获取未读邮件列表。返回邮件的详细信息,包括主题、发件人、正文预览、优先级等。",
        parameters={
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "文件夹名称,默认 INBOX"},
                "limit": {"type": "integer", "description": "最多返回几封,默认 10"},
            },
            "required": [],
        },
        timeout=30.0,
    )
    @plugin_entry(
        id="get_unread",
        name="获取未读邮件",
        description="获取未读邮件列表",
        input_schema={
            "type": "object",
            "properties": {
                "folder": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": [],
        },
        llm_result_fields=["emails"],
    )
    async def get_unread(self, folder: str = "INBOX", limit: int = 10, **_):
        """获取未读邮件"""
        try:
            plugin = self._get_plugin()
            result = plugin.get_unread(folder=folder, limit=limit)
            if isinstance(result, dict) and "error" in result:
                return Err(SdkError(result["error"]))
            return Ok({"emails": result, "count": len(result)})
        except Exception as e:
            return Err(SdkError(f"获取未读邮件失败: {e}"))

    @llm_tool(
        name="neko_mail_search",
        description="搜索邮件。可以按关键词搜索主题、发件人、正文。",
        parameters={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
                "folder": {"type": "string", "description": "文件夹名称,默认 INBOX"},
                "limit": {"type": "integer", "description": "最多返回几封,默认 10"},
            },
            "required": ["keyword"],
        },
        timeout=30.0,
    )
    @plugin_entry(
        id="search",
        name="搜索邮件",
        description="按关键词搜索邮件",
        input_schema={
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "folder": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["keyword"],
        },
        llm_result_fields=["emails"],
    )
    async def search(self, keyword: str, folder: str = "INBOX", limit: int = 10, **_):
        """搜索邮件"""
        try:
            plugin = self._get_plugin()
            result = plugin.search(keyword=keyword, folder=folder, limit=limit)
            if isinstance(result, dict) and "error" in result:
                return Err(SdkError(result["error"]))
            return Ok({"emails": result, "count": len(result), "keyword": keyword})
        except Exception as e:
            return Err(SdkError(f"搜索邮件失败: {e}"))

    @llm_tool(
        name="neko_mail_mark_read",
        description="标记邮件已读。当主人说'标记为已读'、'看过了'等时使用。",
        parameters={
            "type": "object",
            "properties": {
                "uid": {"type": "string", "description": "邮件 UID"},
                "folder": {"type": "string", "description": "文件夹名称,默认 INBOX"},
            },
            "required": ["uid"],
        },
        timeout=15.0,
    )
    @plugin_entry(
        id="mark_read",
        name="标记邮件已读",
        description="标记邮件为已读",
        input_schema={
            "type": "object",
            "properties": {
                "uid": {"type": "string"},
                "folder": {"type": "string"},
            },
            "required": ["uid"],
        },
        llm_result_fields=["success"],
    )
    async def mark_read(self, uid: str, folder: str = "INBOX", **_):
        """标记邮件已读"""
        try:
            plugin = self._get_plugin()
            result = plugin.mark_read(uid=uid, folder=folder)
            if "error" in result:
                return Err(SdkError(result["error"]))
            return Ok(result)
        except Exception as e:
            return Err(SdkError(f"标记已读失败: {e}"))

    @llm_tool(
        name="neko_mail_send",
        description="发送邮件。可以指定收件人、主题、正文,可选抄送。",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "收件人邮箱"},
                "subject": {"type": "string", "description": "邮件主题"},
                "body": {"type": "string", "description": "邮件正文"},
                "cc": {"type": "array", "items": {"type": "string"}, "description": "抄送列表(可选)"},
            },
            "required": ["to", "subject", "body"],
        },
        timeout=30.0,
    )
    @plugin_entry(
        id="send",
        name="发送邮件",
        description="发送邮件",
        input_schema={
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "cc": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["to", "subject", "body"],
        },
        llm_result_fields=["success"],
    )
    async def send(self, to: str, subject: str, body: str, cc: Optional[list] = None, **_):
        """发送邮件"""
        try:
            plugin = self._get_plugin()
            result = plugin.send(to=to, subject=subject, body=body, cc=cc)
            if "error" in result:
                return Err(SdkError(result["error"]))
            return Ok(result)
        except Exception as e:
            return Err(SdkError(f"发送邮件失败: {e}"))

    @llm_tool(
        name="neko_mail_list_folders",
        description="列出邮箱的所有文件夹及未读数。",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        timeout=15.0,
    )
    @plugin_entry(
        id="list_folders",
        name="列出文件夹",
        description="列出邮箱文件夹及未读数",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        llm_result_fields=["folders"],
    )
    async def list_folders(self, **_):
        """列出文件夹"""
        try:
            plugin = self._get_plugin()
            result = plugin.list_folders()
            if isinstance(result, dict) and "error" in result:
                return Err(SdkError(result["error"]))
            return Ok({"folders": result})
        except Exception as e:
            return Err(SdkError(f"列出文件夹失败: {e}"))
