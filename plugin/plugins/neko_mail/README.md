# 📧 猫娘邮件秘书 (Neko Mail)

让猫娘帮你管理 QQ 邮箱,生成邮件摘要、判断优先级、标记已读、发送邮件。

## ✨ 特性

- 🌸 **清新诗意的前端界面** - 白、蓝、粉渐变色,浪漫可爱风格
- 🌍 **支持 i18n 多语言** - 中文、英文、日文、韩文、繁体中文、西班牙文、葡萄牙文、俄文
- 📊 **智能邮件摘要** - 按优先级分类(高/中/低),猫娘友好播报
- 🔍 **关键词搜索** - 搜索主题、发件人、正文
- ✉️ **发送邮件** - 支持收件人、抄送、主题、正文
- 🏷️ **优先级判断** - 自动识别紧急邮件(学校、导师、HR、面试、offer 等)
- 📎 **附件识别** - 显示附件数量和大小
- 🔄 **标记已读** - 一键标记邮件为已读

## 📦 安装

### 方法 1: 使用 neko-plugin-pack 打包安装(推荐)

```bash
# 1. 打包插件
Use Skill: neko-plugin-pack

# 2. 安装插件(会自动安装到 N.E.K.O 项目)
# 打包完成后会生成 .neko-plugin 文件,自动安装

# 3. 重启 N.E.K.O
# 重启后插件会自动加载
```

### 方法 2: 手动安装

```bash
# 1. 复制插件目录到 N.E.K.O 的 plugin/plugins/ 下
cp -r neko_mail /path/to/N.E.K.O/plugin/plugins/

# 2. 重启 N.E.K.O
```

## 🔧 配置

### 步骤 1: 获取 QQ 邮箱授权码

1. 登录 [QQ 邮箱](https://mail.qq.com)
2. 点击「设置」→「账户」
3. 找到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务」
4. 开启「IMAP/SMTP 服务」
5. 按提示生成**授权码**(16 位字母)
6. **重要**: 复制并保存授权码,只显示一次!

### 步骤 2: 配置插件

编辑 `plugin/plugins/neko_mail/plugin.toml`:

```toml
[neko_mail]
# QQ 邮箱地址
email_addr = "你的QQ号@qq.com"

# QQ 邮箱授权码(16 位)
auth_code = "abcdefghijklmnop"

# IMAP 服务器(默认即可)
imap_server = "imap.qq.com"
imap_port = 993

# SMTP 服务器(默认即可)
smtp_server = "smtp.qq.com"
smtp_port = 465

# 高优先级发件人(可选,逗号分隔)
# 匹配发件人地址中的任意子串
high_priority_senders = "导师邮箱@edu.cn,boss@company.com"

# 忽略的文件夹(可选,逗号分隔)
ignore_folders = "广告邮件,订阅邮件"
```

### 步骤 3: 重启 N.E.K.O

重启后,插件会自动加载并连接邮箱。

## 🎯 使用方法

### 方法 1: 通过猫娘对话

直接对猫娘说:

- **「看看今天的邮件」** → 猫娘会调用 `neko_mail_get_summary` 获取今日摘要
- **「有什么紧急邮件吗」** → 猫娘会告诉你高优先级邮件
- **「搜索关于面试的邮件」** → 猫娘会调用 `neko_mail_search` 搜索
- **「标记为已读」** → 猫娘会调用 `neko_mail_mark_read` 标记已读
- **「给 xxx@qq.com 发封邮件」** → 猫娘会调用 `neko_mail_send` 发送邮件

### 方法 2: 通过前端界面

访问 N.E.K.O 的插件面板,找到「猫娘邮件秘书」:

- 📊 **今日摘要** - 查看未读数、今日邮件、高优先级邮件
- 📬 **未读邮件** - 查看所有未读邮件,可一键标记已读
- 🔍 **搜索邮件** - 按关键词搜索
- ✉️ **发送邮件** - 填写收件人、主题、正文,一键发送

### 方法 3: 独立测试脚本

```bash
# 设置环境变量
# Windows PowerShell:
$env:QQ_EMAIL="你的QQ号@qq.com"
$env:QQ_AUTH_CODE="你的授权码"

# Linux/Mac:
export QQ_EMAIL="你的QQ号@qq.com"
export QQ_AUTH_CODE="你的授权码"

# 运行测试
cd plugin/plugins/neko_mail
python test.py
```

测试脚本会:
1. 列出所有文件夹及未读数
2. 获取 3 封未读邮件详情
3. 生成今日邮件摘要

## 🛠️ LLM 工具接口

插件注册了以下 `@llm_tool`,猫娘可以直接调用:

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `neko_mail_get_summary` | 获取今日邮件摘要 | 无 |
| `neko_mail_get_unread` | 获取未读邮件列表 | `folder` (默认 INBOX), `limit` (默认 10) |
| `neko_mail_search` | 搜索邮件 | `keyword` (必填), `folder`, `limit` |
| `neko_mail_mark_read` | 标记邮件已读 | `uid` (必填), `folder` |
| `neko_mail_send` | 发送邮件 | `to`, `subject`, `body` (必填), `cc` (可选) |
| `neko_mail_list_folders` | 列出文件夹 | 无 |

## 🎨 优先级判断规则

### 高优先级 (HIGH)

满足任一条件:
- 发件人域名含 `edu.cn` / `学校` / `教务处` / `导师` / `hr` / `boss`
- 主题含: `紧急`、`重要`、`截止`、`deadline`、`面试`、`offer`、`挂科`、`补考`、`成绩`
- 发件人在 `high_priority_senders` 配置中

### 低优先级 (LOW)

满足任一条件:
- 发件人含 `noreply` / `no-reply` / `notification` / `newsletter` / `marketing` / `ads`
- 主题含: `推广`、`订阅`、`unsubscribe`、`广告`、`优惠`、`促销`、`账单已出`

### 中优先级 (MEDIUM)

其余邮件

## 📂 项目结构

```
neko_mail/
├── __init__.py          # 插件入口,注册 @llm_tool
├── plugin.py            # 插件主类,封装邮件操作
├── client.py            # IMAP/SMTP 客户端
├── parser.py            # 邮件解析(HTML→文本、优先级判断)
├── models.py            # Pydantic 数据模型
├── plugin.toml          # 插件配置
├── test.py              # 独立测试脚本
├── README.md            # 本文档
├── i18n/                # 多语言翻译
│   ├── zh-CN.json
│   ├── en.json
│   ├── ja.json
│   ├── ko.json
│   ├── zh-TW.json
│   ├── es.json
│   ├── pt.json
│   └── ru.json
└── static/
    └── index.html       # 前端界面(清新可爱风格)
```

## 🔒 安全说明

- **授权码安全**: 授权码仅存储在 `plugin.toml`,不会上传或外泄
- **连接加密**: 使用 SSL/TLS 加密连接 IMAP/SMTP 服务器
- **只读模式**: 默认以只读模式获取邮件,仅在标记已读时写入
- **发信确认**: 发送邮件前,建议让猫娘确认收件人和内容

## 🐛 常见问题

### Q: 提示「授权码错误」

A: 检查 `plugin.toml` 中的 `auth_code` 是否正确,注意是**授权码**而不是 QQ 密码。

### Q: 连接超时

A: 检查网络连接,确保能访问 `imap.qq.com:993` 和 `smtp.qq.com:465`。

### Q: 看不到某些文件夹

A: 某些系统文件夹(如 `[Gmail]`)会被自动过滤。如需查看,可修改 `client.py` 中的过滤逻辑。

### Q: 邮件正文乱码

A: 插件支持 UTF-8、GBK、GB2312、Big5、ISO-8859-1 等常见编码,会自动识别。如果仍有乱码,请提 issue。

## 📝 开发计划

- [ ] 支持附件下载
- [ ] 支持 HTML 邮件发送
- [ ] 支持邮件回复
- [ ] 支持定时检查新邮件并推送通知
- [ ] 支持多个邮箱账户
- [ ] 支持 Gmail、Outlook 等其他邮箱

## 🤝 贡献

欢迎提 issue 和 PR!

## 📄 许可证

MIT License

## 💖 致谢

- [imapclient](https://github.com/mjs/imapclient) - IMAP 客户端库
- [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML 解析
- [pydantic](https://github.com/pydantic/pydantic) - 数据模型验证

---

**让猫娘成为你的邮件小秘书吧~** 🐱📧
