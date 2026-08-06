"""
猫娘邮件插件 - IMAP/SMTP 客户端
负责邮件收发、文件夹管理、搜索
"""

import email
import imaplib
import smtplib
from datetime import datetime, date
from typing import Optional
from .models import EmailMessage, Attachment, FolderInfo
from .parser import (
    decode_header_value,
    extract_email_address,
    html_to_text,
    classify_priority,
    parse_attachment,
)


class NekoMailClient:
    """QQ邮箱 IMAP/SMTP 客户端"""
    
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
        self.email_addr = email_addr
        self.auth_code = auth_code
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.high_priority_senders = high_priority_senders or []
        self.ignore_folders = ignore_folders or []
        
        self._imap: Optional[imaplib.IMAP4_SSL] = None
        self._connected = False
    
    def _ensure_connected(self):
        """确保 IMAP 连接可用"""
        if self._imap is None or not self._connected:
            self._connect()
    
    def _connect(self):
        """连接到 IMAP 服务器"""
        try:
            self._imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self._imap.login(self.email_addr, self.auth_code)
            self._connected = True
        except Exception as e:
            self._connected = False
            if "authentication" in str(e).lower() or "login" in str(e).lower():
                raise RuntimeError(f"登录失败: 授权码错误,请检查 .env 中的 QQ_AUTH_CODE")
            raise RuntimeError(f"连接邮箱服务器失败: {e}")
    
    def _reconnect(self):
        """重新连接"""
        self.disconnect()
        self._connect()
    
    def disconnect(self):
        """断开 IMAP 连接"""
        if self._imap:
            try:
                self._imap.logout()
            except Exception:
                pass
        self._imap = None
        self._connected = False
    
    def list_folders(self) -> list[FolderInfo]:
        """列出所有文件夹及未读数"""
        self._ensure_connected()
        
        try:
            status, folder_data = self._imap.list()
            if status != 'OK':
                return []
            
            result = []
            for folder_line in folder_data:
                if folder_line is None:
                    continue
                
                # 解析文件夹信息: (flags) "delimiter" "name"
                folder_str = folder_line.decode('utf-8') if isinstance(folder_line, bytes) else str(folder_line)
                
                # 提取文件夹名称
                import re
                match = re.search(r'"([^"]*)"$', folder_str)
                if not match:
                    continue
                name = match.group(1)
                
                # 跳过忽略的文件夹
                if any(ign.lower() in name.lower() for ign in self.ignore_folders):
                    continue
                
                # 跳过特殊文件夹
                if name.startswith('[') or '\\Noselect' in folder_str:
                    continue
                
                try:
                    self._imap.select(name, readonly=True)
                    status, messages = self._imap.search(None, 'UNSEEN')
                    unread_count = len(messages[0].split()) if status == 'OK' and messages[0] else 0
                    
                    status, all_messages = self._imap.search(None, 'ALL')
                    total_count = len(all_messages[0].split()) if status == 'OK' and all_messages[0] else 0
                    
                    result.append(FolderInfo(
                        name=name,
                        unread_count=unread_count,
                        total_count=total_count,
                    ))
                except Exception:
                    continue
            
            return result
        except Exception as e:
            self._reconnect()
            raise RuntimeError(f"列出文件夹失败: {e}")
    
    def get_unread(self, folder: str = "INBOX", limit: int = 10) -> list[EmailMessage]:
        """获取未读邮件"""
        self._ensure_connected()
        
        try:
            self._imap.select(folder, readonly=True)
            status, messages = self._imap.search(None, 'UNSEEN')
            
            if status != 'OK' or not messages[0]:
                return []
            
            uids = messages[0].split()
            
            # 取最新的 limit 封
            uids = uids[-limit:]
            
            emails = []
            for uid in uids:
                try:
                    email_msg = self._fetch_email(uid, folder)
                    if email_msg:
                        emails.append(email_msg)
                except Exception:
                    continue
            
            return emails
        except Exception as e:
            self._reconnect()
            raise RuntimeError(f"获取未读邮件失败: {e}")
    
    def search(self, keyword: str, folder: str = "INBOX", limit: int = 10) -> list[EmailMessage]:
        """关键词搜索主题+正文+发件人"""
        self._ensure_connected()
        
        try:
            self._imap.select(folder, readonly=True)
            
            # IMAP 搜索: 主题、发件人、正文
            criteria = [
                f'(SUBJECT "{keyword}")',
                f'(FROM "{keyword}")',
                f'(BODY "{keyword}")',
            ]
            
            all_uids = set()
            for crit in criteria:
                try:
                    status, messages = self._imap.search(None, crit)
                    if status == 'OK' and messages[0]:
                        all_uids.update(messages[0].split())
                except Exception:
                    continue
            
            if not all_uids:
                return []
            
            # 取最新的 limit 封
            uids = sorted(all_uids, key=lambda x: int(x))[-limit:]
            
            emails = []
            for uid in uids:
                try:
                    email_msg = self._fetch_email(uid, folder)
                    if email_msg:
                        emails.append(email_msg)
                except Exception:
                    continue
            
            return emails
        except Exception as e:
            self._reconnect()
            raise RuntimeError(f"搜索邮件失败: {e}")
    
    def get_today_emails(self, folder: str = "INBOX") -> list[EmailMessage]:
        """获取今日邮件"""
        self._ensure_connected()
        
        try:
            self._imap.select(folder, readonly=True)
            
            today = date.today()
            since_str = today.strftime("%d-%b-%Y")
            
            status, messages = self._imap.search(None, f'(SINCE {since_str})')
            
            if status != 'OK' or not messages[0]:
                return []
            
            uids = messages[0].split()
            
            emails = []
            for uid in uids:
                try:
                    email_msg = self._fetch_email(uid, folder)
                    if email_msg:
                        emails.append(email_msg)
                except Exception:
                    continue
            
            return emails
        except Exception as e:
            self._reconnect()
            raise RuntimeError(f"获取今日邮件失败: {e}")
    
    def _fetch_email(self, uid: bytes, folder: str) -> Optional[EmailMessage]:
        """获取单封邮件详情"""
        try:
            status, data = self._imap.fetch(uid, '(RFC822 FLAGS)')
            
            if status != 'OK' or not data or not data[0]:
                return None
            
            # data[0] 是一个元组: (b'1 (FLAGS (...))', b'邮件内容')
            raw_email = data[0][1]
            
            # 解析 FLAGS
            flags_str = data[0][0].decode('utf-8') if isinstance(data[0][0], bytes) else str(data[0][0])
            import re
            flags_match = re.search(r'FLAGS \(([^)]*)\)', flags_str)
            flags = flags_match.group(1).split() if flags_match else []
            
            # 解析邮件
            msg = email.message_from_bytes(raw_email)
            
            # 提取字段
            subject = decode_header_value(msg.get('Subject', ''))
            sender = extract_email_address(msg.get('From', ''))
            
            # 收件人
            to_header = msg.get('To', '')
            recipients = [extract_email_address(addr) for addr in to_header.split(',')]
            recipients = [r for r in recipients if r]
            
            # 抄送
            cc_header = msg.get('Cc', '')
            cc = [extract_email_address(addr) for addr in cc_header.split(',')]
            cc = [c for c in cc if c]
            
            # 日期
            date_str = msg.get('Date', '')
            try:
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(date_str)
            except Exception:
                email_date = datetime.now()
            
            # 正文和附件
            body_text = ""
            body_html = ""
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    # 附件
                    if 'attachment' in content_disposition:
                        att = parse_attachment(part)
                        if att:
                            attachments.append(att)
                    else:
                        # 正文
                        if content_type == 'text/plain':
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or 'utf-8'
                                try:
                                    body_text += payload.decode(charset, errors='replace')
                                except Exception:
                                    body_text += payload.decode('utf-8', errors='replace')
                        elif content_type == 'text/html':
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or 'utf-8'
                                try:
                                    body_html += payload.decode(charset, errors='replace')
                                except Exception:
                                    body_html += payload.decode('utf-8', errors='replace')
            else:
                # 单部分邮件
                content_type = msg.get_content_type()
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    try:
                        text = payload.decode(charset, errors='replace')
                    except Exception:
                        text = payload.decode('utf-8', errors='replace')
                    
                    if content_type == 'text/html':
                        body_html = text
                    else:
                        body_text = text
            
            # HTML 转文本
            if body_html and not body_text:
                body_text = html_to_text(body_html)
            
            # 附件摘要
            if attachments:
                att_summary = "\n\n" + "📎 附件: " + ", ".join(
                    f"{a.filename} ({a.size_human()})" for a in attachments
                )
                body_text += att_summary
            
            # 创建邮件对象
            email_msg = EmailMessage(
                uid=str(uid),
                subject=subject,
                sender=sender,
                recipients=recipients,
                cc=cc,
                date=email_date,
                body_text=body_text,
                body_html=body_html if body_html else None,
                attachments=attachments,
                flags=[f.decode() if isinstance(f, bytes) else f for f in flags],
                priority="medium",  # 稍后分类
                folder=folder,
            )
            
            # 分类优先级
            email_msg.priority = classify_priority(email_msg, self.high_priority_senders)
            
            return email_msg
        except Exception as e:
            return None
    
    def mark_read(self, uid: str, folder: str = "INBOX") -> bool:
        """标记邮件已读"""
        self._ensure_connected()
        
        try:
            self._imap.select(folder)
            self._imap.store(uid.encode(), '+FLAGS', '\\Seen')
            return True
        except Exception as e:
            self._reconnect()
            return False
    
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[list[str]] = None,
        html: bool = False,
    ) -> bool:
        """发送邮件"""
        try:
            # 懒加载 email.mime 模块（避免 Windows multiprocessing spawn 子进程顶层导入失败）
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.email_addr
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            if html:
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 所有收件人
            recipients = [to]
            if cc:
                recipients.extend(cc)
            
            # 发送
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.email_addr, self.auth_code)
                server.sendmail(self.email_addr, recipients, msg.as_string())
            
            return True
        except Exception as e:
            raise RuntimeError(f"发送邮件失败: {e}")
