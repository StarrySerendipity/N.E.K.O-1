"""OpenCode Adapter — OpenCode CLI 子进程执行器。

负责：
1. 检测 OpenCode CLI 可执行文件（跨平台）
2. 构建 CLI 参数列表（参考 paperclip opencode-local execute.ts）
3. 启动子进程并通过 stdin 传入 prompt
4. 逐行读取 stdout，交给解析器处理
5. 处理超时和进程终止

OpenCode CLI 调用模式（来自 paperclip opencode-local execute.ts）::

    opencode run --format json --model <provider/model>
                 [--session <session_id>]
                 [--variant <variant>]
                 [extra_args...]

    # prompt 通过 stdin 传入

参考：
- ``paperclip/packages/adapters/opencode-local/src/server/execute.ts``
- ``N.E.K.O/plugin/plugins/cursor_adapter/executor.py`` 的子进程管理
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from typing import Any, Optional

from .errors import (
    CLI_NOT_FOUND,
    ClassifiedError,
    TIMEOUT,
    classify_error,
)
from .models import AdapterConfig, CLIInvocation
from .parser import OpenCodeOutputParser, ParsedOpenCodeStream


# ---------------------------------------------------------------------------
# 跨平台 CLI 检测
# ---------------------------------------------------------------------------


def is_windows() -> bool:
    return sys.platform == "win32"


def detect_opencode_cli() -> Optional[str]:
    """寻找 OpenCode CLI 可执行文件。

    检测顺序：
    - ``opencode``（npm 全局安装后的命令名）
    - ``opencode.exe``（Windows 显式扩展名）
    - ``opencode.cmd`` / ``opencode.bat``（Windows npm 全局 shim）
    """
    candidates = ["opencode"]
    if is_windows():
        for name in candidates:
            for ext in (".exe", ".cmd", ".bat", ""):
                candidate = shutil.which(name + ext) if ext else shutil.which(name)
                if candidate:
                    return candidate
        return None

    for name in candidates:
        candidate = shutil.which(name)
        if candidate:
            return candidate
    return None


# ---------------------------------------------------------------------------
# CLI 参数构建
# ---------------------------------------------------------------------------


def build_cli_invocation(
    config: AdapterConfig,
    *,
    prompt: str,
    resume_session_id: str = "",
    cwd: Optional[str] = None,
    model: str = "",
    variant: str = "",
) -> tuple[CLIInvocation, Optional[ClassifiedError]]:
    """构建一次 OpenCode CLI 调用。

    参数构建顺序参考 paperclip opencode-local execute.ts::

        opencode run --format json --model <provider/model>
                      [--session <session_id>]
                      [--variant <variant>]
                      [extra_args...]

    prompt 通过 stdin 传入（不放在命令行参数中）。

    Returns
    -------
    invocation:
        CLI 调用参数。
    error:
        如果 CLI 未找到或参数非法，返回错误；否则 None。
    """
    # 1. 解析可执行文件路径
    exe_path = (config.command or "").strip() or detect_opencode_cli() or ""
    if not exe_path:
        placeholder = CLIInvocation(
            cmd=[],
            cwd=cwd or config.cwd or os.getcwd(),
            stdin_data=prompt.encode("utf-8"),
            timeout=float(config.timeout_sec),
        )
        return placeholder, ClassifiedError(
            kind=CLI_NOT_FOUND,
            message=(
                "OpenCode CLI not found in PATH. "
                "Install via 'npm install -g opencode-ai' or set "
                "[opencode].command in plugin.toml."
            ),
            retryable=False,
        )

    # 2. 解析调用参数（调用参数 > 配置默认值）
    effective_model = (model or config.model or "").strip()
    effective_variant = (variant or config.variant or "").strip()

    # 3. 构建参数列表（顺序参考 paperclip opencode-local execute.ts）
    effective_cwd = cwd or config.cwd or os.getcwd()

    # Windows 上 .cmd/.bat shim 需要通过 cmd.exe /c 执行
    exe_lower = exe_path.lower()
    if is_windows() and (exe_lower.endswith(".cmd") or exe_lower.endswith(".bat")):
        cmd: list[str] = ["cmd.exe", "/c", exe_path]
    else:
        cmd: list[str] = [exe_path]

    # core 命令: run --format json
    cmd.extend(["run", "--format", "json"])

    # 模型（provider/model 格式，必填）
    cmd.extend(["--model", effective_model])

    # 会话恢复
    if resume_session_id:
        cmd.extend(["--session", resume_session_id])

    # 推理变体
    if effective_variant:
        cmd.extend(["--variant", effective_variant])

    # 额外参数
    if config.extra_args:
        cmd.extend(config.extra_args)

    # 4. 处理 instructions_file_path：读取文件内容并前置到 prompt
    final_prompt = prompt
    instructions_path = (config.instructions_file_path or "").strip()
    if instructions_path:
        try:
            with open(instructions_path, "r", encoding="utf-8") as f:
                instructions_content = f.read()
            final_prompt = f"{instructions_content}\n\n---\n\nUser Task:\n{prompt}"
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to read instructions_file_path %s: %s", instructions_path, e
            )

    # 5. 构建 invocation
    invocation = CLIInvocation(
        cmd=cmd,
        cwd=effective_cwd,
        stdin_data=final_prompt.encode("utf-8"),
        timeout=float(config.timeout_sec),
    )
    return invocation, None


# ---------------------------------------------------------------------------
# 子进程执行器
# ---------------------------------------------------------------------------


class OpenCodeCLIExecutor:
    """OpenCode CLI 子进程执行器。

    封装 ``asyncio.create_subprocess_exec``，提供：
    - 跨平台 spawn（Windows 由 ``detect_opencode_cli`` 处理）
    - stdin 写入 prompt
    - stdout 逐行读取并交给解析器
    - stderr 收集（用于错误诊断）
    - 超时处理和进程终止
    """

    def __init__(self, config: AdapterConfig, logger: Any = None) -> None:
        self.config = config
        self.logger = logger

    async def execute(
        self,
        invocation: CLIInvocation,
        parser: OpenCodeOutputParser,
    ) -> tuple[ParsedOpenCodeStream, Optional[ClassifiedError]]:
        """执行一次 CLI 调用。

        Parameters
        ----------
        invocation:
            CLI 调用参数（由 ``build_cli_invocation`` 构建）。
        parser:
            流式输出解析器。每行 stdout 会被喂给 ``parser.parse_line``。

        Returns
        -------
        stream:
            解析后的完整流。
        error:
            如果执行失败，返回分类后的错误；否则 None。
        """
        if not invocation.cmd:
            return parser.finalize(), ClassifiedError(
                kind=CLI_NOT_FOUND,
                message="OpenCode CLI not found",
                retryable=False,
            )

        if self.logger is not None:
            try:
                self.logger.info(
                    "OpenCode CLI invoke: cmd=%s cwd=%s stdin_len=%d timeout=%s",
                    invocation.cmd,
                    invocation.cwd,
                    len(invocation.stdin_data),
                    invocation.timeout,
                )
            except Exception:
                pass

        # 合并环境变量
        env = os.environ.copy()
        env.update(invocation.env_overrides)

        try:
            proc = await asyncio.create_subprocess_exec(
                *invocation.cmd,
                cwd=invocation.cwd,
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            return parser.finalize(), ClassifiedError(
                kind=CLI_NOT_FOUND,
                message=f"OpenCode CLI not found: {e}",
                retryable=False,
            )
        except Exception as e:
            return parser.finalize(), classify_error(str(e))

        # 收集 stderr
        stderr_lines: list[str] = []

        async def _read_stderr() -> None:
            if proc.stderr is None:
                return
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                stderr_lines.append(
                    line.decode("utf-8", errors="replace").rstrip("\r\n")
                )

        # 读取 stdout 并喂给解析器
        async def _read_stdout() -> None:
            if proc.stdout is None:
                return
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                try:
                    parser.parse_line(line)
                except Exception as e:
                    if self.logger is not None:
                        try:
                            self.logger.warning("Failed to parse stdout line: %s", e)
                        except Exception:
                            pass

        stderr_task = asyncio.create_task(_read_stderr())
        stdout_task = asyncio.create_task(_read_stdout())

        # 写入 stdin 并关闭
        try:
            if proc.stdin is not None:
                proc.stdin.write(invocation.stdin_data)
                await proc.stdin.drain()
                proc.stdin.close()
        except Exception as e:
            if self.logger is not None:
                try:
                    self.logger.warning("Failed to write stdin: %s", e)
                except Exception:
                    pass

        # 等待进程结束（带超时）
        try:
            return_code = await asyncio.wait_for(
                proc.wait(), timeout=invocation.timeout
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            await _drain_tasks(stdout_task, stderr_task)
            stderr_text = "\n".join(stderr_lines)
            return parser.finalize(), ClassifiedError(
                kind=TIMEOUT,
                message=(
                    f"execution timed out after {invocation.timeout}s. "
                    f"stderr: {stderr_text[:500]}"
                ),
                retryable=False,
            )

        await _drain_tasks(stdout_task, stderr_task)

        stream = parser.finalize()
        stderr_text = "\n".join(stderr_lines)

        # 优先使用流中的错误事件
        if stream.is_error:
            error_msg = stream.error_message or stderr_text or (
                f"process exited with code {return_code}"
            )
            err = classify_error(
                error_msg,
                stdout=_stream_to_text(stream),
                stderr=stderr_text,
                return_code=return_code,
            )
            return stream, err

        # 返回码非零但没有错误事件
        if return_code != 0:
            err = classify_error(
                stderr_text or f"process exited with code {return_code}",
                stderr=stderr_text,
                return_code=return_code,
            )
            return stream, err

        # 成功
        return stream, None


def _stream_to_text(stream: ParsedOpenCodeStream) -> str:
    """将解析后的流转换为纯文本（用于错误分类的 haystack）。"""
    parts: list[str] = []
    if stream.session_id:
        parts.append(f"sessionID={stream.session_id}")
    for msg in stream.text_messages:
        if msg.text:
            parts.append(msg.text)
    if stream.error_message:
        parts.append(stream.error_message)
    return "\n".join(parts)


async def _drain_tasks(*tasks: asyncio.Task) -> None:
    """等待所有任务结束，忽略异常。"""
    for task in tasks:
        try:
            await task
        except Exception:
            pass


__all__ = [
    "is_windows",
    "detect_opencode_cli",
    "build_cli_invocation",
    "OpenCodeCLIExecutor",
]