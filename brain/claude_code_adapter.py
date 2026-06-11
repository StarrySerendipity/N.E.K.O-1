# -*- coding: utf-8 -*-
"""Claude Code Adapter.

将 Claude Code (Anthropic 的 AI 编程代理) 作为 N.E.K.O 猫娘的一个外部编码执行渠道。
猫娘的 Agent 系统可以把编程/代码审查/文件操作类任务委派给 Claude Code 执行。

调用方式（两种模式）：
1. CLI subprocess 模式（默认）：通过 `claude` CLI 命令执行一次性任务
2. SDK 会话模式（需要 claude-code-sdk）：通过 Python SDK 保持持久会话

CLI 命令要求：
  - Node.js 18+
  - npm install -g @anthropic-ai/claude-code
  - ANTHROPIC_API_KEY 环境变量或 claude 已登录认证

环境变量（可选覆盖）：
  NEKO_CLAUDE_CODE_CLI_PATH    — claude 可执行文件路径（默认 "claude"）
  NEKO_CLAUDE_CODE_TIMEOUT     — 单次任务超时秒数（默认 600）
  NEKO_CLAUDE_CODE_MAX_TOKENS  — Claude Code 输出 token 上限（默认 8000）
  NEKO_CLAUDE_CODE_SESSIONS_DIR — 会话持久化目录（默认 {data_dir}/claude_code_sessions）
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ─── 环境变量读取 ───

def _env_str(name: str, default: str) -> str:
    raw = os.getenv(f"NEKO_{name}")
    return raw if raw else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(f"NEKO_{name}")
    if raw:
        try:
            return int(raw)
        except (ValueError, TypeError):
            pass
    return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(f"NEKO_{name}")
    if raw:
        try:
            return float(raw)
        except (ValueError, TypeError):
            pass
    return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(f"NEKO_{name}")
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# ─── 状态枚举 ───

class ClaudeCodeStatus(str, Enum):
    """Claude Code 任务状态。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


# ─── 数据类 ───

@dataclass
class ClaudeCodeTask:
    """一个 Claude Code 任务的上下文。"""
    task_id: str
    prompt: str
    working_dir: str = "."
    status: ClaudeCodeStatus = ClaudeCodeStatus.PENDING
    session_id: Optional[str] = None
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    cost_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaudeCodeConfig:
    """Claude Code 配置。

    由 config_manager 动态管理，此处提供默认值和 env 覆盖。
    """
    # CLI 路径
    cli_path: str = "claude"
    # 超时（秒）
    timeout: int = 600
    # 输出 token 上限
    max_tokens: int = 8000
    # 会话持久化目录
    sessions_dir: str = ""
    # 是否允许 Claude Code 修改文件（危险操作！默认开启以支持编码任务）
    allow_file_edits: bool = True
    # 是否允许执行 Bash 命令
    allow_bash: bool = True
    # 自定义 system prompt 前缀（会拼在用户 prompt 之前）
    system_prefix: str = ""
    # 代理设置
    proxy: str = ""
    # 最大重试次数
    max_retries: int = 1
    # 是否启用权限模式（"acceptEdits" 或 "default"）
    permission_mode: str = "default"
    # 是否允许危险操作（如 rm -rf）
    allow_dangerous: bool = False

    def __post_init__(self):
        if not self.sessions_dir:
            # 默认使用 N.E.K.O 数据目录下的子目录
            if platform.system() == "Windows":
                appdata = os.environ.get("APPDATA", "")
                base = os.path.join(appdata, "N.E.K.O") if appdata else ""
            elif platform.system() == "Darwin":
                base = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "N.E.K.O")
            else:
                base = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "N.E.K.O")
            self.sessions_dir = os.path.join(base, "claude_code_sessions") if base else "/tmp/neko_claude_sessions"


# ─── 核心 Adapter ───

class ClaudeCodeAdapter:
    """N.E.K.O → Claude Code 适配器。

    用法示例：
        adapter = ClaudeCodeAdapter(config)
        result = await adapter.execute(
            task_id="task_001",
            prompt="创建一个 Python Flask API，支持 /health 端点",
            working_dir="/workspace/my_project",
            on_progress=lambda msg: print(f"进度: {msg}"),
        )
    """

    def __init__(self, config: Optional[ClaudeCodeConfig] = None):
        self.config = config or ClaudeCodeConfig()
        # 从环境变量覆盖
        self.config.cli_path = _env_str("CLAUDE_CODE_CLI_PATH", self.config.cli_path)
        self.config.timeout = _env_int("CLAUDE_CODE_TIMEOUT", self.config.timeout)
        self.config.max_tokens = _env_int("CLAUDE_CODE_MAX_TOKENS", self.config.max_tokens)
        # 确保 sessions 目录存在
        os.makedirs(self.config.sessions_dir, exist_ok=True)
        # 活跃会话 {session_id: ClaudeCodeTask}
        self._active_tasks: dict[str, ClaudeCodeTask] = {}
        self._available: Optional[bool] = None

    async def check_available(self) -> bool:
        """检查 Claude Code CLI 是否可用。"""
        if self._available is not None:
            return self._available

        cli = self.config.cli_path
        try:
            proc = await asyncio.create_subprocess_exec(
                cli, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode == 0:
                version = stdout.decode().strip() if stdout else "unknown"
                logger.info("Claude Code CLI 可用: %s", version)
                self._available = True
                return True
            else:
                err = stderr.decode().strip() if stderr else "unknown error"
                logger.warning("Claude Code CLI 不可用 (rc=%d): %s", proc.returncode, err)
                self._available = False
                return False
        except FileNotFoundError:
            logger.warning("Claude Code CLI 未找到: %s", cli)
            self._available = False
            return False
        except asyncio.TimeoutError:
            logger.warning("Claude Code CLI 检查超时")
            self._available = False
            return False
        except Exception as e:
            logger.warning("Claude Code CLI 检查异常: %s", e)
            self._available = False
            return False

    async def execute(
        self,
        task_id: str,
        prompt: str,
        working_dir: str = ".",
        session_id: Optional[str] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """执行一个 Claude Code 任务。

        Args:
            task_id: 任务唯一标识
            prompt: 给 Claude Code 的指令
            working_dir: 工作目录（Claude Code 在此目录读写文件）
            session_id: 可选的会话 ID，用于保持跨轮次上下文
            on_progress: 进度回调函数，接收字符串消息

        Returns:
            {
                "success": bool,
                "output": str,       # Claude Code 的最终输出
                "error": str,        # 错误信息（如有）
                "exit_code": int,    # 进程退出码
                "task_id": str,
                "session_id": str,   # 使用的会话 ID
                "duration_seconds": float,
                "metadata": dict,
            }
        """
        task = ClaudeCodeTask(
            task_id=task_id,
            prompt=prompt,
            working_dir=working_dir,
            session_id=session_id or f"{task_id}_session",
        )
        self._active_tasks[task_id] = task

        if not await self.check_available():
            return self._fail(task, "Claude Code CLI 不可用。请安装 @anthropic-ai/claude-code")

        # 验证工作目录
        work_dir = os.path.abspath(working_dir)
        if not os.path.isdir(work_dir):
            return self._fail(task, f"工作目录不存在: {work_dir}")

        task.status = ClaudeCodeStatus.RUNNING
        task.started_at = time.time()

        try:
            result = await self._run_cli_task(task, work_dir, on_progress)
        except asyncio.TimeoutError:
            task.status = ClaudeCodeStatus.TIMEOUT
            task.completed_at = time.time()
            duration = task.completed_at - task.started_at if task.started_at else 0
            return {
                "success": False,
                "output": task.output,
                "error": f"任务超时（{self.config.timeout}秒）",
                "exit_code": -1,
                "task_id": task_id,
                "session_id": task.session_id or "",
                "duration_seconds": round(duration, 2),
                "metadata": task.metadata,
            }
        except asyncio.CancelledError:
            task.status = ClaudeCodeStatus.CANCELLED
            task.completed_at = time.time()
            return self._fail(task, "任务被取消")
        except Exception as e:
            return self._fail(task, str(e))

    async def _run_cli_task(
        self,
        task: ClaudeCodeTask,
        work_dir: str,
        on_progress: Optional[Callable[[str], None]],
    ) -> dict[str, Any]:
        """通过 CLI subprocess 执行 Claude Code 任务。

        使用 --output-format stream-json 模式以获得结构化输出和进度流。
        """
        # 构建完整 prompt
        full_prompt = self._build_prompt(task)

        # 构建 claude 命令
        cmd = [self.config.cli_path]

        # 使用 -p 传入 prompt（一次性任务模式）
        cmd.extend(["-p", full_prompt])

        # 输出格式：stream-json 可以解析进度
        cmd.extend(["--output-format", "stream-json"])

        # 权限模式
        if self.config.permission_mode:
            cmd.extend(["--permission-mode", self.config.permission_mode])

        # 如果允许危险操作
        if self.config.allow_dangerous:
            cmd.append("--dangerously-skip-permissions")

        # 设置 Anthropic API key（如果配置中提供了）
        env = os.environ.copy()
        # 确保工作目录
        cwd = work_dir

        logger.info("启动 Claude Code: task=%s cwd=%s", task.task_id, cwd)
        if on_progress:
            on_progress(f"🔧 启动 Claude Code...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,  # 非交互模式
            cwd=cwd,
            env=env,
        )

        output_parts: list[str] = []
        error_parts: list[str] = []

        # 并发读取 stdout 和 stderr
        async def read_stdout():
            assert proc.stdout is not None
            async for line in proc.stdout:
                text = line.decode("utf-8", errors="replace")
                # 尝试解析 JSON 行
                try:
                    data = json.loads(text.strip())
                    if isinstance(data, dict):
                        msg_type = data.get("type", "")
                        if msg_type == "result":
                            output_parts.append(data.get("output", ""))
                        elif msg_type == "assistant":
                            # Claude Code 的思考过程
                            thinking = data.get("message", "")
                            if thinking and on_progress:
                                on_progress(f"💭 {thinking[:200]}")
                        elif msg_type == "error":
                            error_parts.append(data.get("error", text))
                        else:
                            output_parts.append(text)
                    else:
                        output_parts.append(text)
                except json.JSONDecodeError:
                    # 非 JSON 输出，直接收集
                    stripped = text.strip()
                    if stripped:
                        output_parts.append(stripped)

        async def read_stderr():
            assert proc.stderr is not None
            async for line in proc.stderr:
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    error_parts.append(text)
                    if on_progress:
                        on_progress(f"⚠️ {text[:200]}")

        try:
            # 并发读取，带超时
            await asyncio.wait_for(
                asyncio.gather(read_stdout(), read_stderr()),
                timeout=self.config.timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise

        # 等待进程结束
        exit_code = await proc.wait()

        output = "\n".join(output_parts).strip()
        error = "\n".join(error_parts).strip()

        task.output = output
        task.error = error
        task.exit_code = exit_code
        task.status = ClaudeCodeStatus.COMPLETED if exit_code == 0 else ClaudeCodeStatus.FAILED
        task.completed_at = time.time()

        duration = task.completed_at - task.started_at if task.started_at else 0

        logger.info(
            "Claude Code 完成: task=%s exit=%d duration=%.1fs output_len=%d",
            task.task_id, exit_code, duration, len(output),
        )

        return {
            "success": exit_code == 0,
            "output": output,
            "error": error,
            "exit_code": exit_code,
            "task_id": task.task_id,
            "session_id": task.session_id or "",
            "duration_seconds": round(duration, 2),
            "metadata": task.metadata,
        }

    def _build_prompt(self, task: ClaudeCodeTask) -> str:
        """构建发送给 Claude Code 的完整 prompt。"""
        parts = []

        # System prefix（来自配置）
        if self.config.system_prefix:
            parts.append(self.config.system_prefix)

        # 添加角色定位前缀（让 Claude Code 知道自己是猫娘的编码助手）
        parts.append(
            "你是 N.E.K.O 猫娘助手的编码执行代理。"
            "请根据以下要求完成任务。"
            "完成后简要总结你做了什么。"
            "如果任务涉及读取或修改文件，请确保操作正确。"
        )

        # 用户指令
        parts.append(f"\n\n任务指令：\n{task.prompt}")

        return "\n".join(parts)

    def _fail(self, task: ClaudeCodeTask, error: str) -> dict[str, Any]:
        """构建失败响应。"""
        task.status = ClaudeCodeStatus.FAILED
        task.error = error
        task.completed_at = time.time()
        duration = task.completed_at - task.started_at if task.started_at else 0

        return {
            "success": False,
            "output": task.output,
            "error": error,
            "exit_code": task.exit_code,
            "task_id": task.task_id,
            "session_id": task.session_id or "",
            "duration_seconds": round(duration, 2),
            "metadata": task.metadata,
        }

    async def cancel_task(self, task_id: str) -> bool:
        """取消一个运行中的任务。"""
        task = self._active_tasks.get(task_id)
        if task and task.status == ClaudeCodeStatus.RUNNING:
            task.status = ClaudeCodeStatus.CANCELLED
            task.completed_at = time.time()
            logger.info("Claude Code 任务已取消: %s", task_id)
            return True
        return False

    def get_task_status(self, task_id: str) -> Optional[dict[str, Any]]:
        """查询任务状态。"""
        task = self._active_tasks.get(task_id)
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "session_id": task.session_id,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "output_len": len(task.output),
            "error": task.error,
        }

    def cleanup_old_sessions(self, max_age_days: int = 7) -> int:
        """清理超过 N 天的会话目录。"""
        if not os.path.isdir(self.config.sessions_dir):
            return 0
        cutoff = time.time() - (max_age_days * 86400)
        cleaned = 0
        for entry in os.listdir(self.config.sessions_dir):
            path = os.path.join(self.config.sessions_dir, entry)
            try:
                if os.path.isdir(path) and os.path.getmtime(path) < cutoff:
                    shutil.rmtree(path)
                    cleaned += 1
            except OSError as e:
                logger.warning("清理旧会话失败: %s: %s", path, e)
        logger.info("清理了 %d 个过期 Claude Code 会话", cleaned)
        return cleaned


# ─── 模块级单例（供 task_executor 使用） ───

_adapter: Optional[ClaudeCodeAdapter] = None
_adapter_lock = asyncio.Lock() if not hasattr(asyncio, "_lock_created_for_claude") else None


def get_claude_code_adapter(config: Optional[ClaudeCodeConfig] = None) -> ClaudeCodeAdapter:
    """获取或创建 ClaudeCodeAdapter 单例。"""
    global _adapter
    if _adapter is None:
        _adapter = ClaudeCodeAdapter(config)
    return _adapter


def reset_claude_code_adapter() -> None:
    """重置单例（测试用）。"""
    global _adapter
    _adapter = None
