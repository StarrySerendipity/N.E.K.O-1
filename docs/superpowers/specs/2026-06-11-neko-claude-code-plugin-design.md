# N.E.K.O. × Claude Code 插件设计文档

> 日期: 2026-06-11
> 状态: 已批准
> 目标: 让猫娘通过插件调用 Claude Code 执行编程任务

---

## 1. 概述

### 1.1 目标

开发一个 N.E.K.O. 插件，使猫娘 LLM 能够通过 `@llm_tool` 调用 Claude Code CLI 来执行编程任务，包括：
- 写代码、创建项目
- 修复 bug、重构代码
- 运行终端命令、安装依赖
- 多轮对话，保持上下文

### 1.2 约束

- **只动插件，不动主项目**：所有代码在 `plugin/claude_code/` 目录下
- **完整权限**：Claude Code 可以读/写文件、执行终端命令、安装依赖
- **后台执行 + 汇报**：猫娘在后台调用 Claude Code，完成后汇报结果
- **Claude Code 已安装**：假设 `claude` 命令已可用

---

## 2. 技术方案

### 2.1 架构

采用 Claude Code SDK 控制协议（stdin/stdout 交互式模式）：

```
猫娘 LLM
    │
    ▼
ClaudeCodeTool (@llm_tool)
    │
    ▼
SessionPool (会话池)
    │
    ├── ClaudeCodeSession A ─── claude 子进程 A (stdin/stdout)
    ├── ClaudeCodeSession B ─── claude 子进程 B (stdin/stdout)
    └── ClaudeCodeSession C ─── claude 子进程 C (stdin/stdout)
```

### 2.2 Claude Code SDK 协议

Claude Code 支持通过 `--output-format stream-json` 启动 SDK 模式，通过 stdin/stdout 交换 JSON 消息：

**启动：**
```bash
claude --output-format stream-json --allowedTools Read,Write,Edit,Bash --permission-mode acceptEdits
```

**控制消息（stdin → Claude）：**
- `control_request` with `subtype: "initialize"` — 初始化会话
- `user` message — 发送用户消息

**事件流（stdout ← Claude）：**
- `init` — 初始化完成
- `assistant` — Claude 回复
- `user` — 用户消息（echo）
- `tool_use` — 工具调用
- `tool_result` — 工具结果
- `result` — 任务完成（含统计信息）

### 2.3 核心组件

#### 2.3.1 ClaudeCodeSession

管理单个 Claude Code 子进程会话。

```python
class ClaudeCodeSession:
    """管理单个 Claude Code 交互式会话"""

    属性:
        session_id: str     — 会话唯一 ID
        proc: asyncio.subprocess — Claude 子进程
        status: str         — idle / busy / done
        working_dir: str    — 工作目录

    方法:
        async start(system_prompt: str) → None
            — 发送 initialize 请求，启动后台读取任务

        async send_message(text: str) → dict
            — 发送用户消息，等待 result 事件

        async cancel() → None
            — 终止子进程

        list_sessions() → list[dict]
            — 列出所有会话状态
```

#### 2.3.2 SessionPool

管理所有 Claude Code 会话的生命周期。

```python
class SessionPool:
    """会话池：创建、查找、清理 Claude Code 会话"""

    方法:
        async create_session(
            working_dir: str = "",
            max_turns: int = 50,
            allowed_tools: str = "Read,Write,Edit,Bash",
            system_prompt: str = "",
        ) → str
            — 启动 claude 子进程，发送 initialize，返回 session_id

        async send_message(session_id: str, text: str) → dict
            — 向指定会话发送消息并等待完成

        async cancel_session(session_id: str) → None
            — 取消指定会话

        async cancel_all() → None
            — 取消所有活跃会话（插件卸载时调用）

        list_sessions() → list[dict]
            — 列出所有会话及其状态
```

#### 2.3.3 ClaudeCodeTool

LLM 工具入口。

```python
@llm_tool(
    name="claude_code",
    description="调用 Claude Code 执行编程任务",
)
class ClaudeCodeTool:
    """
    纯交互式 Claude Code SDK 模式集成。

    通过 stdin/stdout 控制协议与 Claude Code 进程通信，
    支持多轮对话、持续任务、进度查询和会话管理。
    """

    工具参数:
        action: Literal["start", "send", "cancel", "list"]
            — 操作类型
        session_id: str = ""
            — 目标会话 ID（send/cancel/list 时需要）
        message: str = ""
            — 发送的消息内容（send 时需要）
        working_dir: str = ""
            — 工作目录（start 时需要，空则用用户主目录）
        max_turns: int = 50
            — 最大轮数（start 时可选）
        allowed_tools: str = "Read,Write,Edit,Bash"
            — 允许的工具列表（start 时可选）
        system_prompt: str = ""
            — 额外系统提示（start 时可选）
```

---

## 3. 文件结构

```
plugin/claude_code/
├── __init__.py                    # 空文件，标记为 Python 包
└── claude_code_tool.py            # 主实现 (~200-250 行)
    ├── ClaudeCodeSession 类        # 单个会话管理
    ├── SessionPool 类             # 会话池管理
    └── ClaudeCodeTool 类          # LLM 工具入口
```

---

## 4. 数据流

### 4.1 新建会话 + 发送消息

```
1. 猫娘 LLM 调用:
   claude_code(action="start", working_dir="/workspace", system_prompt="你是猫娘的编程助手")

2. 插件内部:
   - 生成 session_id: "neko-cc-{uuid4()[:8]}"
   - 启动 claude 子进程:
     claude --output-format stream-json \
       --allowedTools Read,Write,Edit,Bash \
       --permission-mode acceptEdits
   - 发送 initialize 请求（含 system_prompt）
   - 启动后台 asyncio.Task 读取 stdout
   - 注册到 SessionPool

3. 返回:
   {"success": true, "session_id": "neko-cc-abc123"}

4. 猫娘 LLM 调用:
   claude_code(action="send", session_id="neko-cc-abc123",
               message="帮我写个贪吃蛇游戏，用 Python+pygame")

5. 插件内部:
   - 查找 SessionPool 中的会话
   - 发送 user message 到 stdin
   - 从 _event_queue 读取事件，直到 result
   - 提取结果文本

6. 返回:
   {"success": true, "result": "已创建 snake_game.py...", "events": [...]}
```

### 4.2 多轮对话

```
1. 猫娘看到结果后，决定继续:
   claude_code(action="send", session_id="neko-cc-abc123",
               message="再添加一个暂停功能和分数排行榜")

2. 因为同一 session_id，Claude 记住之前的上下文
3. Claude 继续执行，返回新结果
```

### 4.3 取消任务

```
1. 猫娘决定取消:
   claude_code(action="cancel", session_id="neko-cc-abc123")

2. 插件:
   - proc.kill()
   - await proc.wait()
   - 从 SessionPool 移除
```

---

## 5. 错误处理

| 场景 | 处理方式 |
|------|----------|
| `claude` 命令不存在 | 返回 "Claude Code 未安装，请先运行 `npm install -g @anthropic-ai/claude-code`" |
| 进程启动失败 | 记录 stderr，返回错误信息 |
| stdout 读取超时（60s 无数据） | 返回 "Claude Code 长时间无响应，可能需要更长时间或已卡住" |
| session_id 不存在 | 返回 "会话不存在，可能已被取消或超时" |
| 插件卸载时有活跃会话 | SessionPool.cancel_all() 清理所有子进程 |
| Claude Code 返回错误 | 透传错误信息给猫娘 |
| stdout JSON 解析失败 | 跳过该行，继续读取 |

---

## 6. 超时与资源管理

| 参数 | 值 | 说明 |
|------|-----|------|
| 插件总超时 | 300 秒 | N.E.K.O. 系统限制 |
| send_message 超时 | 280 秒 | 留 20 秒余量 |
| stdout 读取心跳超时 | 60 秒 | 60 秒无数据视为异常 |
| 进程清理 | 插件卸载时 | SessionPool.cancel_all() |

---

## 7. 猫娘 LLM 提示词

集成到 N.E.K.O. 的 `config/neko_config.yaml` 中：

```yaml
system_prompt_addition: |
  ## 🛠️ Claude Code 编程工具

  当需要执行编程任务（写代码、修复 bug、创建项目、运行命令等）时，
  使用 Claude Code 工具。

  ### 可用操作：

  1. **start** - 启动新的 Claude Code 会话
     - working_dir: 工作目录
     - system_prompt: 额外的指导
     - max_turns: 最大轮数（默认 50）
     - allowed_tools: 允许的工具（默认 Read,Write,Edit,Bash）

  2. **send** - 向会话发送消息
     - session_id: 目标会话 ID
     - message: 要发送的内容

  3. **cancel** - 取消会话
     - session_id: 目标会话 ID

  4. **list** - 列出所有活跃会话

  ### 使用示例：
  主人说"帮我写个贪吃蛇"，你：
  1. 先 start 创建会话
  2. 再 send 发送具体指令
  3. 完成后告诉主人结果
```
