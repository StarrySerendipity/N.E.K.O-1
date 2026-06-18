# Transcript Race Condition Bug

## 问题描述

随着对话轮数增加，插件开始推送**上一轮**的消息而不是当前轮的消息。

## 根本原因

时序竞争问题

```
Claude Code完成回复 → 触发Stop hook
        ↓
但此时transcript可能还在写入（OS缓存、异步写入）
        ↓
插件读取到的是不完整的transcript（上一轮的内容）
        ↓
推送了上一轮的消息
```

## 为什么随对话增加更容易出现

- 对话轮数越多，Claude一次执行的工具调用越多
- transcript写入时间越长
- hook触发时transcript未完成的概率越大

## 尝试过的修复方案（已弃用）

**Commit**: ff46e875

在解析transcript之前，等待文件稳定（不再被写入）：

```python
# 等待 transcript 文件稳定
last_size = -1
for _ in range(10):  # 最多等1秒
    try:
        current_size = os.path.getsize(transcript_path)
    except OSError:
        break
    if current_size == last_size:
        break  # 文件大小没变化，说明写入完成
    last_size = current_size
    time.sleep(0.1)  # 等100ms
```

### 为什么弃用

该修复方案引入了新的bug：**插件无法正常收到 Claude 的 http hooks**。

**根本原因**：`_on_turn_end()` 是同步执行的，`time.sleep()` 阻塞了 HTTP 响应。

```
Claude Code 触发 Stop hook
        ↓
发送 HTTP POST 到 127.0.0.1:48920/hook/turn-end
        ↓
HTTP handler 调用 _on_turn_end()（同步执行）
        ↓
_on_turn_end() 中执行 time.sleep(0.1) × 10次
        ↓
HTTP 响应被阻塞，最多延迟 1 秒
        ↓
Claude Code 等待响应（timeout=10秒）
        ↓
可能导致超时或线程阻塞
```

**关键点**：Claude Code 发送 HTTP 请求后会**等待响应**，如果响应延迟，Claude Code 也会延迟。

## 正确的修复方向

**核心思想**：让 HTTP 响应立即返回，把耗时操作放到后台执行。

```python
def _handle_turn_end(self, data: dict):
    """处理 Stop hook - 异步执行"""
    if self.plugin_instance:
        # 在新线程中执行，不阻塞 HTTP 响应
        threading.Thread(
            target=self.plugin_instance._on_turn_end,
            args=(data,),
            daemon=True
        ).start()
    self._respond(200, {"status": "ok"})  # 立即返回
```

### 为什么这是正确的修复方向

1. **HTTP hook 的本质**：Claude Code 发送 hook 只是**通知**，不需要等待处理结果
2. **解耦**：hook 触发和消息处理应该解耦，互不影响
3. **可靠性**：即使消息处理失败，也不影响 Claude Code 继续执行
4. **可以安全等待**：后台线程可以安全地执行 `time.sleep()`，不影响任何人

### 好处

- ✅ 不阻塞 Claude Code
- ✅ 不超时
- ✅ 可以安全等待 transcript 文件稳定
- ✅ 即使消息处理失败，也不影响 Claude Code 继续执行

## 待探索的替代方案

1. **异步执行 + 等待文件稳定**（推荐）：在新线程中执行 `_on_turn_end()`，可以安全等待
2. **改进解析逻辑**：不要求assistant消息必须有text才算找到
3. **记录轮次状态**：在UserPromptSubmit hook时记录用户消息

## 相关文件

- 插件代码：`plugin/plugins/claude_companion/__init__.py`
- 解析方法：`TranscriptParser.parse_latest_turn()`
- Hook处理：`_on_turn_end()`

## 状态

- [ ] 待修复
