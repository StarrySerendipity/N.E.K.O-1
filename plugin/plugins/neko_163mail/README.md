# 📧 neko_163mail - 网易邮箱助手

网易163邮箱管理插件，为N.E.K.O-1提供邮件读取、发送、搜索等功能。

## ✨ 功能特性

- 📬 **邮件读取** - 支持未读邮件、全部邮件、文件夹浏览
- ✉️ **邮件发送** - 支持发送邮件（含附件支持）
- 🔍 **邮件搜索** - 按关键词搜索邮件
- ✅ **标记已读** - 单封/批量标记已读
- 📎 **附件支持** - 查看附件列表，发送带附件邮件
- 🏷️ **智能分类** - 自动分类邮件（验证码、作业、安全通知等）
- 📊 **监控面板** - 操作时间线、重要邮件日志、分类统计、待处理事项
- 🔔 **新邮件轮询** - 自动检测新邮件并推送通知

## ⚙️ 配置

插件配置在 `plugin.toml` 中：

```toml
[config]
email_addr = "19221693657@163.com"
auth_code = "NMctpmgdG476GuYL"
imap_server = "imap.163.com"
imap_port = 993
smtp_server = "smtp.163.com"
smtp_port = 465
```

## 🎯 LLM 工具

插件向LLM暴露以下工具：

| 工具名 | 功能 |
|--------|------|
| `neko_163mail_send` | 发送邮件（支持附件） |
| `neko_163mail_read` | 读取未读邮件 |
| `neko_163mail_read_all` | 读取全部邮件 |
| `neko_163mail_search` | 搜索邮件 |
| `neko_163mail_mark_read` | 标记邮件已读 |
| `neko_163mail_delete` | 删除邮件 |
| `neko_163mail_folders` | 列出文件夹 |
| `neko_163mail_monitor` | 查看邮件监控状态 |
| `neko_163mail_operation_logs` | 查看操作日志 |
| `neko_163mail_important_emails` | 查看重要邮件日志 |
| `neko_163mail_category_stats` | 查看分类统计 |
| `neko_163mail_pending_items` | 查看待处理事项 |

## 🎨 前端界面

清新明亮的蓝白色调，诗意浪漫的风格：
- 🌸 白、蓝、粉渐变色系
- ✨ 悬浮动画效果
- 📱 响应式设计
- 🐱 猫娘风格提示语

## 📁 文件结构

```
neko_163mail/
├── plugin.toml      # 插件配置
├── __init__.py      # 插件入口，LLM工具定义
├── plugin.py        # 插件主类
├── client.py        # IMAP/SMTP客户端
├── models.py        # 数据模型
├── parser.py        # 邮件解析
├── operation_log.py # 操作日志
├── static/
│   └── index.html   # 前端界面
├── i18n/
│   ├── zh-CN.json   # 中文翻译
│   └── en-US.json   # 英文翻译
└── README.md        # 本文件
```

## 📝 版本历史

- v0.1.0 (2026-08-08) - 初始版本
  - 基础邮件功能（读取/发送/搜索/删除）
  - 附件支持
  - 智能分类
  - 监控面板
  - 操作日志
  - 新邮件轮询
