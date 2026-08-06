"""
猫娘邮件插件 - 插件主类
提供猫娘可调用的邮件操作接口

v0.2 优化:
  - get_today_summary 使用轻量级邮件头方法,速度提升10倍+
  - 新增 get_all_emails 接口,支持已读+未读邮件列表
  - 新增 get_email_detail 接口,按需加载完整邮件
"""

from datetime import datetime, date
from typing import Optional
from .client import NekoMailClient
from .models import EmailMessage, EmailSummary, EmailSnippet, FolderInfo


class NekoMailPlugin:
    """猫娘邮件插件主类"""
    
    def __init__(
        self,
        email_addr: str,
        auth_code: str,
        imap_server: str = "imap.qq.com",
        imap_port: int = 993,
        smtp_server: str = "smtp.qq.com",
        smtp_port: int = 465,
        high_priority_senders: Optional[list[str]] = None,
        ignore_folders: Optional[list[str]] = None,
    ):
        self.client = NekoMailClient(
            email_addr=email_addr,
            auth_code=auth_code,
            imap_server=imap_server,
            imap_port=imap_port,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            high_priority_senders=high_priority_senders,
            ignore_folders=ignore_folders,
        )
    
    # === 读取类 ===
    
    def list_folders(self) -> list[dict]:
        """列出所有文件夹及未读数"""
        try:
            folders = self.client.list_folders()
            return [
                {
                    "name": f.name,
                    "unread_count": f.unread_count,
                    "total_count": f.total_count,
                }
                for f in folders
            ]
        except Exception as e:
            return {"error": str(e)}
    
    def get_unread(self, folder: str = "INBOX", limit: int = 50, offset: int = 0) -> list[dict]:
        """获取未读邮件 (轻量级邮件头,不下载正文)，支持分页"""
        try:
            emails = self.client.get_unread_headers(folder=folder, limit=limit, offset=offset)
            total = self.client.get_unread_count(folder=folder)
            return {
                "emails": [self._header_to_dict(e) for e in emails],
                "total": total,
                "offset": offset,
                "count": len(emails)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_all_emails(self, folder: str = "INBOX", limit: int = 50, offset: int = 0) -> dict:
        """获取所有邮件 (已读+未读,轻量级邮件头)，支持分页"""
        try:
            emails = self.client.get_all_emails_headers(folder=folder, limit=limit, offset=offset)
            total = self.client.get_all_emails_count(folder=folder)
            return {
                "emails": [self._header_to_dict(e) for e in emails],
                "total": total,
                "offset": offset,
                "count": len(emails)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_email_detail(self, uid: str, folder: str = "INBOX") -> dict:
        """获取单封邮件完整详情 (含正文和附件)"""
        try:
            email_msg = self.client.get_email_detail(uid=uid, folder=folder)
            if email_msg:
                return self._email_to_dict(email_msg)
            return {"error": "邮件未找到"}
        except Exception as e:
            return {"error": str(e)}
    
    def search(self, keyword: str, folder: str = "INBOX", limit: int = 100, offset: int = 0) -> dict:
        """关键词搜索主题+正文+发件人，支持分页"""
        try:
            emails = self.client.search(keyword=keyword, folder=folder, limit=limit, offset=offset)
            total = self.client.search_count(keyword=keyword, folder=folder)
            return {
                "emails": [self._email_to_dict(e) for e in emails],
                "total": total,
                "offset": offset,
                "count": len(emails)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_today_summary(self) -> dict:
        """今日邮件摘要,按优先级分类 (使用轻量级方法)"""
        try:
            # 轻量级: 只获取邮件头,不下载正文
            today_headers = self.client.get_today_emails_headers()
            unread_headers = self.client.get_unread_headers(limit=50)
            
            high = []
            medium = []
            low = []
            
            for h in today_headers:
                snippet = EmailSnippet(
                    uid=h["uid"],
                    subject=h["subject"],
                    sender=h["sender"],
                    preview="",  # 轻量级没有正文预览
                    time=h["date"].strftime("%H:%M"),
                    priority=h["priority"],
                    folder=h["folder"],
                )
                
                if h["priority"] == "high":
                    high.append(snippet)
                elif h["priority"] == "low":
                    low.append(snippet)
                else:
                    medium.append(snippet)
            
            summary = EmailSummary(
                total_unread=len(unread_headers),
                total_today=len(today_headers),
                high_priority=high,
                medium_priority=medium,
                low_priority=low,
            )
            
            return {
                "total_unread": summary.total_unread,
                "total_today": summary.total_today,
                "high_priority": [s.model_dump() for s in summary.high_priority],
                "medium_priority": [s.model_dump() for s in summary.medium_priority],
                "low_priority": [s.model_dump() for s in summary.low_priority],
                "catgirl_text": summary.to_catgirl_text(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    # === 操作类 ===
    
    def mark_read(self, uid: str, folder: str = "INBOX") -> dict:
        """标记已读"""
        try:
            success = self.client.mark_read(uid=uid, folder=folder)
            return {"success": success, "uid": uid}
        except Exception as e:
            return {"error": str(e)}
    
    def batch_mark_read(self, uids: list[str], folder: str = "INBOX") -> dict:
        """批量标记邮件已读"""
        try:
            result = self.client.batch_mark_read(uids=uids, folder=folder)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def mark_all_read(self, folder: str = "INBOX") -> dict:
        """标记文件夹内所有邮件为已读"""
        try:
            result = self.client.mark_all_read(folder=folder)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[list[str]] = None,
    ) -> dict:
        """发送邮件"""
        try:
            success = self.client.send(to=to, subject=subject, body=body, cc=cc)
            return {"success": success, "to": to, "subject": subject}
        except Exception as e:
            return {"error": str(e)}
    
    # === 辅助方法 ===
    
    def _header_to_dict(self, h: dict) -> dict:
        """将邮件头 dict 转换为前端需要的格式"""
        return {
            "uid": h["uid"],
            "subject": h["subject"],
            "sender": h["sender"],
            "recipients": h.get("recipients", []),
            "cc": h.get("cc", []),
            "date": h["date"].isoformat() if h.get("date") else "",
            "body_text": "",
            "attachments": [],
            "flags": h.get("flags", []),
            "priority": h.get("priority", "medium"),
            "folder": h.get("folder", "INBOX"),
            "preview": "",
            "time_str": h["date"].strftime("%Y-%m-%d %H:%M") if h.get("date") else "",
            "has_attachments": h.get("has_attachments", False),
        }
    
    def _email_to_dict(self, email: EmailMessage) -> dict:
        """将 EmailMessage 转换为字典"""
        return {
            "uid": email.uid,
            "subject": email.subject,
            "sender": email.sender,
            "recipients": email.recipients,
            "cc": email.cc,
            "date": email.date.isoformat(),
            "body_text": email.body_text,
            "attachments": [
                {
                    "filename": a.filename,
                    "size": a.size,
                    "content_type": a.content_type,
                    "size_human": a.size_human(),
                }
                for a in email.attachments
            ],
            "flags": email.flags,
            "priority": email.priority,
            "folder": email.folder,
            "preview": email.preview(200),
            "time_str": email.time_str(),
            "has_attachments": email.has_attachments(),
        }
    
    def close(self):
        """关闭连接"""
        self.client.disconnect()
