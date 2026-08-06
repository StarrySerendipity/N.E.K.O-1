"""
猫娘邮件插件 - 邮件解析器
负责 HTML 转文本、附件提取、优先级判断
"""

import re
from email.header import decode_header
from email.utils import parseaddr
from typing import Optional
from bs4 import BeautifulSoup
from .models import EmailMessage, Attachment


def decode_header_value(value: str) -> str:
    """解码邮件头(支持 RFC2047 编码)"""
    if not value:
        return ""
    
    decoded_parts = []
    for part, charset in decode_header(value):
        if isinstance(part, bytes):
            try:
                charset = charset or 'utf-8'
                decoded_parts.append(part.decode(charset, errors='replace'))
            except (LookupError, UnicodeDecodeError):
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(part)
    
    return ''.join(decoded_parts)


def extract_email_address(header_value: str) -> str:
    """从邮件头提取邮箱地址"""
    if not header_value:
        return ""
    name, email = parseaddr(header_value)
    return email or header_value


def html_to_text(html: str, max_length: int = 8000) -> str:
    """
    HTML 转纯文本
    - 保留段落(用 \n\n 分隔)
    - <a href="url">文本</a> → "文本(url)"
    - 移除脚本、样式、注释
    - 超过 max_length 字符截断
    """
    if not html:
        return ""
    
    # 解析 HTML
    soup = BeautifulSoup(html, 'html.parser')
    
    # 移除不需要的标签
    for tag in soup(['script', 'style', 'head', 'meta', 'link']):
        tag.decompose()
    
    # 处理链接: <a href="url">文本</a> → "文本(url)"
    for a_tag in soup.find_all('a'):
        href = a_tag.get('href', '')
        text = a_tag.get_text(strip=True)
        if href and text:
            a_tag.replace_with(f"{text}({href})")
        elif text:
            a_tag.replace_with(text)
        else:
            a_tag.decompose()
    
    # 处理段落和换行
    for tag in soup.find_all(['p', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
        tag.insert_before('\n')
        tag.insert_after('\n')
    
    # 提取文本
    text = soup.get_text()
    
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = '\n'.join(line.strip() for line in text.splitlines())
    
    # 截断
    if len(text) > max_length:
        text = text[:max_length] + "\n\n...(已截断)"
    
    return text.strip()


def classify_priority(
    email: EmailMessage,
    high_priority_senders: Optional[list[str]] = None
) -> str:
    """
    判断邮件优先级
    
    HIGH 如果满足任一:
    - 发件人域名含 edu.cn / 学校 / 教务处 / 导师 / hr / boss
    - 主题含: 紧急、重要、截止、deadline、面试、offer、挂科、补考、成绩
    - 发件人在用户配置的高优先级白名单里
    
    LOW 如果满足任一:
    - 发件人含 noreply / no-reply / notification / newsletter / marketing / ads
    - 主题含: 推广、订阅、unsubscribe、广告、优惠、促销、账单已出
    
    其余为 MEDIUM
    """
    sender_lower = email.sender.lower()
    subject_lower = email.subject.lower()
    
    # 高优先级关键词
    high_keywords = [
        '紧急', '重要', '截止', 'deadline', '面试', 'offer', 
        '挂科', '补考', '成绩', 'urgent', 'important'
    ]
    
    # 高优先级域名/发件人
    high_domains = ['edu.cn', '学校', '教务处', '导师', 'hr', 'boss']
    
    # 低优先级关键词
    low_keywords = [
        '推广', '订阅', 'unsubscribe', '广告', '优惠', '促销', 
        '账单已出', 'newsletter', 'marketing'
    ]
    
    # 低优先级发件人
    low_senders = ['noreply', 'no-reply', 'notification', 'newsletter', 'marketing', 'ads']
    
    # 检查高优先级
    # 1. 主题关键词
    if any(kw in subject_lower for kw in high_keywords):
        return 'high'
    
    # 2. 发件人域名
    if any(domain in sender_lower for domain in high_domains):
        return 'high'
    
    # 3. 用户配置的高优先级发件人
    if high_priority_senders:
        for sender_pattern in high_priority_senders:
            if sender_pattern.lower() in sender_lower:
                return 'high'
    
    # 检查低优先级
    # 1. 发件人包含低优先级标识
    if any(sender in sender_lower for sender in low_senders):
        return 'low'
    
    # 2. 主题包含低优先级关键词
    if any(kw in subject_lower for kw in low_keywords):
        return 'low'
    
    # 默认为中等优先级
    return 'medium'


def parse_attachment(part) -> Optional[Attachment]:
    """解析邮件附件部分"""
    filename = part.get_filename()
    if not filename:
        return None
    
    # 解码文件名
    filename = decode_header_value(filename)
    
    # 获取大小(估算)
    payload = part.get_payload(decode=True)
    size = len(payload) if payload else 0
    
    # 获取 MIME 类型
    content_type = part.get_content_type()
    
    return Attachment(
        filename=filename,
        size=size,
        content_type=content_type
    )
