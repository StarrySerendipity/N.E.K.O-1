# Kimi WebBridge 浏览器自动化插件

> 通过Kimi WebBridge控制用户真实浏览器，实现导航、点击、填表、截图、数据提取等操作

## 功能特性

### 核心功能
- **导航控制**：在浏览器中导航到指定URL
- **元素交互**：点击、填写表单、获取页面快照
- **数据提取**：从网页提取结构化数据
- **截图功能**：对网页进行截图保存
- **JavaScript执行**：在页面中执行自定义JavaScript代码
- **会话管理**：管理浏览器标签页和会话

### 特色功能
- **多语言支持**：支持中文、英文、日文界面
- **实时状态显示**：显示Kimi WebBridge连接状态
- **可视化操作**：提供直观的Web界面进行操作
- **错误处理**：完善的错误提示和日志记录
- **会话保持**：支持长时间运行的任务会话

## 安装步骤

### 前置条件
1. **Python 3.11**：项目要求Python 3.11环境
2. **N.E.K.O. 项目**：需要已安装并运行N.E.K.O.项目
3. **Kimi WebBridge**：需要先安装Kimi WebBridge守护进程

### 安装Kimi WebBridge
```powershell
# Windows PowerShell
irm https://cdn.kimi.com/webbridge/install.ps1 | iex

# 升级到最新版本
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" upgrade

# 检查安装状态
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" status
```

### 安装插件
1. 将插件目录复制到 `plugin/plugins/` 目录下
2. 重启N.E.K.O.服务
3. 插件会自动加载

## 配置说明

### 插件配置文件
插件配置文件为 `config.json`，包含以下配置项：

```json
{
  "default_session": "webbridge-session",  // 默认会话ID
  "auto_start_daemon": true,               // 是否自动启动守护进程
  "timeout": 30,                           // 操作超时时间（秒）
  "language": "zh-CN",                     // 界面语言
  "ui": {
    "theme": "light",                      // 界面主题
    "animations": true                     // 是否启用动画
  },
  "logging": {
    "level": "info",                       // 日志级别
    "file": "kimi_webbridge.log"           // 日志文件
  }
}
```

### 环境变量
可以通过环境变量覆盖配置：
- `KIMI_WEBBRIDGE_SESSION`：默认会话ID
- `KIMI_WEBBRIDGE_TIMEOUT`：超时时间
- `KIMI_WEBBRIDGE_LANGUAGE`：界面语言

## 使用教程

### 基本使用流程

#### 1. 启动插件
插件会在N.E.K.O.服务启动时自动加载。可以通过Web界面访问：
```
http://localhost:48911/plugin/kimi_webbridge
```

#### 2. 连接状态检查
在插件界面中，首先检查连接状态：
- 绿色圆点：已连接，可以正常使用
- 红色圆点：未连接，需要检查Kimi WebBridge安装

#### 3. 导航到网页
1. 在URL输入框中输入目标网址
2. 选择是否在新标签页中打开
3. 点击"前往"按钮

#### 4. 页面操作
- **快照**：获取当前页面的可访问性树，用于后续操作
- **截图**：对当前页面进行截图保存
- **标签页**：查看所有打开的标签页
- **关闭会话**：关闭当前会话的所有标签页
- **执行JS**：在页面中执行JavaScript代码

### 高级使用技巧

#### 数据提取示例
```javascript
// 提取B站视频信息
(() => {
  const title = document.querySelector(".video-title")?.textContent.trim();
  const desc = document.querySelector(".desc-info-text")?.textContent.trim();
  const up = document.querySelector(".up-name")?.textContent.trim();
  return JSON.stringify({ title, desc, up });
})()
```

#### 自动化表单填写
1. 使用"快照"获取页面元素
2. 找到输入框的`@e`引用
3. 使用"填写"功能输入内容
4. 点击提交按钮

#### 批量数据采集
1. 导航到目标网站
2. 使用JavaScript提取数据
3. 保存结果到文件
4. 导航到下一页重复操作

## API接口

### 插件入口点

| 入口点 | 参数 | 说明 |
|--------|------|------|
| `navigate` | `url`, `new_tab`, `group_title`, `session` | 导航到URL |
| `snapshot` | `session` | 获取页面快照 |
| `click` | `selector`, `session` | 点击元素 |
| `fill` | `selector`, `value`, `session` | 填写表单 |
| `screenshot` | `format`, `quality`, `selector`, `path`, `session` | 截图 |
| `evaluate` | `code`, `session` | 执行JavaScript |
| `list_tabs` | `session` | 列出标签页 |
| `close_session` | `session` | 关闭会话 |
| `set_language` | `language` | 设置语言 |
| `get_status` | - | 获取状态 |

### HTTP API调用示例
```bash
# 导航到URL
curl -X POST http://localhost:48916/plugin/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "plugin_id": "kimi_webbridge",
    "entry_id": "navigate",
    "args": {
      "url": "https://www.bilibili.com",
      "new_tab": true,
      "session": "my-session"
    }
  }'
```

## 故障排除

### 常见问题

#### 1. 连接失败
**症状**：状态显示红色圆点，提示"未连接"
**解决方案**：
```powershell
# 检查Kimi WebBridge是否安装
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" status

# 启动守护进程
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" start
```

#### 2. 操作超时
**症状**：操作长时间无响应
**解决方案**：
- 检查网络连接
- 增加配置中的`timeout`值
- 重启Kimi WebBridge守护进程

#### 3. 编码错误
**症状**：中文字符显示为乱码
**解决方案**：
- 确保使用UTF-8编码
- 检查系统区域设置
- 使用插件提供的API接口

#### 4. 元素找不到
**症状**：点击或填写操作失败
**解决方案**：
- 重新获取页面快照
- 检查元素选择器是否正确
- 等待页面完全加载

### 日志查看
插件日志保存在：
```
plugin/plugins/kimi_webbridge/data/kimi_webbridge.log
```

## 开发指南

### 代码结构
```
kimi_webbridge/
├── __init__.py          # 插件主入口
├── plugin.toml          # 插件配置
├── config.json          # 默认配置
├── README.md            # 本文档
└── static/              # Web界面
    ├── index.html       # 主页面
    ├── styles.css       # 样式文件
    ├── script.js        # 交互逻辑
    └── i18n.js          # 国际化支持
```

### 扩展开发
1. 在`__init__.py`中添加新的入口点
2. 使用`@plugin_entry`装饰器定义接口
3. 实现相应的业务逻辑
4. 更新`input_schema`定义参数

### 测试
```bash
# 测试插件加载
curl -X POST http://localhost:48916/plugin/list

# 测试导航功能
curl -X POST http://localhost:48916/plugin/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "plugin_id": "kimi_webbridge",
    "entry_id": "navigate",
    "args": {"url": "https://example.com"}
  }'
```

## 贡献指南

### 提交代码
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

### 代码规范
- 遵循PEP 8 Python代码规范
- 使用类型注解
- 编写文档字符串
- 添加单元测试

### 问题反馈
- 通过GitHub Issues反馈问题
- 提供详细的错误信息
- 包含复现步骤

## 更新日志

### v1.0.0 (2026-06-17)
- 初始版本发布
- 实现基本浏览器自动化功能
- 支持多语言界面
- 提供Web管理界面

## 许可证

MIT License - 详见项目根目录LICENSE文件

## 致谢

- **Kimi WebBridge**：提供浏览器自动化底层支持
- **N.E.K.O. Project**：提供插件系统框架
- **社区贡献者**：感谢所有贡献者的支持

---

**技术支持**：如有问题，请查看Kimi WebBridge官方文档
- 英文：https://www.kimi.com/features/webbridge
- 中文：https://www.kimi.com/zh-cn/features/webbridge