"""
猫娘邮件插件 - 插件主类
提供猫娘可调用的邮件操作接口
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
    
    def get_unread(self, folder: str = "INBOX", limit: int = 50) -> list[dict]:
        """获取未读邮件,完整解析"""
        try:
            emails = self.client.get_unread(folder=folder, limit=limit)
            return [self._email_to_dict(e) for e in emails]
        except Exception as e:
            return {"error": str(e)}
    
    def search(self, keyword: str, folder: str = "INBOX", limit: int = 10) -> list[dict]:
        """关键词搜索主题+正文+发件人"""
        try:
            emails = self.client.search(keyword=keyword, folder=folder, limit=limit)
            return [self._email_to_dict(e) for e in emails]
        except Exception as e:
            return {"error": str(e)}
    
    def get_today_summary(self) -> dict:
        """今日邮件摘要,按优先级分类"""
        try:
            today_emails = self.client.get_today_emails()
            unread_emails = self.client.get_unread(limit=50)
            
            high = []
            medium = []
            low = []
            
            for e in today_emails:
                snippet = EmailSnippet(
                    uid=e.uid,
                    subject=e.subject,
                    sender=e.sender,
                    preview=e.preview(100),
                    time=e.time_str("%H:%M"),
                    priority=e.priority,
                    folder=e.folder,
                )
                
                if e.priority == "high":
                    high.append(snippet)
                elif e.priority == "low":
                    low.append(snippet)
                else:
                    medium.append(snippet)
            
            summary = EmailSummary(
                total_unread=len(unread_emails),
                total_today=len(today_emails),
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
    
    # === 工具类 ===
    
    def get_sender_priority(self, sender: str) -> str:
        """判断发件人优先级(用于猫娘决策)"""
        sender_lower = sender.lower()
        
        # 高优先级域名/发件人
        high_domains = ['edu.cn', '学校', '教务处', '导师', 'hr', 'boss']
        if any(domain in sender_lower for domain in high_domains):
            return 'high'
        
        # 用户配置的高优先级发件人
        if self.client.high_priority_senders:
            for pattern in self.client.high_priority_senders:
                if pattern.lower() in sender_lower:
                    return 'high'
        
        # 低优先级发件人
        low_senders = ['noreply', 'no-reply', 'notification', 'newsletter', 'marketing', 'ads']
        if any(s in sender_lower for s in low_senders):
            return 'low'
        
        return 'medium'
    
    # === 辅助方法 ===
    
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
