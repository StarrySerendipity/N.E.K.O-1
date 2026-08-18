"""OpenCode Adapter Plugin

通过 @llm_tool 将 OpenCode CLI 注册为猫娘可调用的工具集。

猫娘可以通过以下工具调用 OpenCode 执行开发任务：
- opencode_execute: 执行 OpenCode 任务（写代码、改 bug、跑测试、查文档等）
- opencode_check_health: 检查 OpenCode CLI 是否可用
- opencode_list_sessions: 列出所有会话
- opencode_clear_session: 清除会话记录
- opencode_get_config: 获取当前适配器配置

设计参考：
- Paperclip ``opencode-local`` 适配器的执行流程（packages/adapters/opencode-local）
- N.E.K.O ``cursor_adapter`` 插件的 Plugin 范式

与 Cursor 适配器的关键差异：
- CLI 命令：``opencode run --format json --model <provider/model>``
  （而非 ``cursor-agent -p --output-format stream-json --workspace <cwd>``）
- 会话 ID：``sessionID``（而非 ``session_id``），从 JSONL 事件读取
- 会话恢复：``--session <id>``（而非 ``--resume <id>``）
- 推理变体：``--variant <low|medium|high>``（而非 ``--mode agent/build/ask/browse``）
- 输出格式：JSONL（而非 stream-json），每行一个 JSON 对象
- 安装：``npm install -g opencode-ai``
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Optional

from plugin.sdk.plugin import (
    NekoPluginBase,
    neko_plugin,
    plugin_entry,
    lifecycle,
    llm_tool,
    Ok,
    Err,
    SdkError,
)

from .models import AdapterConfig, ExecuteResult
from .errors import (
    ClassifiedError,
    is_retryable,
    TRANSIENT_UPSTREAM,
)
from .executor import (
    OpenCodeCLIExecutor,
    build_cli_invocation,
    detect_opencode_cli,
)
from .parser import OpenCodeOutputParser
from .session import SessionManager, compute_prompt_signature


def _compute_retry_wait_seconds(retry_not_before: str) -> int:
    """计算从当前时间到 retry_not_before 的等待秒数。"""
    try:
        target_dt = datetime.fromisoformat(retry_not_before)
        if target_dt.tzinfo is not None:
            from datetime import timezone
            now_dt = datetime.now(timezone.utc)
            target_dt = target_dt.astimezone(timezone.utc)
        else:
            now_dt = datetime.now()
        delta = (target_dt - now_dt).total_seconds()
        return max(0, int(delta))
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# 插件主类
# ---------------------------------------------------------------------------


@neko_plugin
class OpenCodeAdapterPlugin(NekoPluginBase):
    """OpenCode 适配器插件。

    通过 @llm_tool 装饰器将 OpenCode CLI 的能力暴露给猫娘 LLM。
    猫娘可以在对话中调用这些工具，让 OpenCode 执行具体的编码任务。
    """

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.file_logger = self.enable_file_logging(log_level="INFO")
        self.logger = self.file_logger

        self._config: AdapterConfig = AdapterConfig()
        self._executor: Optional[OpenCodeCLIExecutor] = None
        self._session_mgr: Optional[SessionManager] = None
        self._ready: bool = False

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    @lifecycle(id="startup")
    async def startup(self, **_) -> Any:
        """启动：加载配置、初始化会话管理器和执行器。"""
        try:
            # 1. 加载 plugin.toml 的 [opencode] 节
            cfg_dict = await self._load_config_section("opencode")
            self._config = AdapterConfig.from_config_dict(cfg_dict)

            # 2. 确保 PluginStore 已启用（用于会话持久化）
            if not self.store.enabled:
                self.store.enabled = True
                self.logger.info("PluginStore auto-enabled for session persistence")

            # 3. 初始化会话管理器
            self._session_mgr = SessionManager(self.store, logger=self.logger)
            await self._session_mgr.load()

            # 4. 初始化执行器
            self._executor = OpenCodeCLIExecutor(self._config, logger=self.logger)

            # 5. 检测 OpenCode CLI 是否可用
            cli_path = self._config.command or detect_opencode_cli() or ""
            cli_available = bool(cli_path)

            self._ready = True
            self.logger.info(
                "OpenCodeAdapter started: cli_available=%s model=%r variant=%r cwd=%r",
                cli_available,
                self._config.model,
                self._config.variant,
                self._config.cwd or os.getcwd(),
            )

            return Ok(
                {
                    "status": "ready",
                    "cli_available": cli_available,
                    "cli_path": cli_path or "",
                    "model": self._config.model,
                    "variant": self._config.variant,
                    "sessions_loaded": len(self._session_mgr)
                    if self._session_mgr
                    else 0,
                }
            )
        except Exception as e:
            self.logger.exception("OpenCodeAdapter startup failed")
            return Err(SdkError(f"startup failed: {e}"))

    @lifecycle(id="shutdown")
    async def shutdown(self, **_) -> Any:
        """关闭：释放资源。"""
        self._ready = False
        self.logger.info("OpenCodeAdapter shutdown")
        return Ok({"status": "shutdown"})

    # ------------------------------------------------------------------
    # 配置加载辅助
    # ------------------------------------------------------------------

    async def _load_config_section(self, section: str) -> dict[str, Any]:
        """从 plugin.toml 加载指定节。"""
        try:
            cfg = await self.config.dump(timeout=5.0)
            if isinstance(cfg, dict):
                section_data = cfg.get(section)
                if isinstance(section_data, dict):
                    return section_data
        except Exception as e:
            self.logger.warning("Failed to load config section %s: %s", section, e)
        return {}

    def _ensure_ready(self) -> Optional[Any]:
        """检查插件是否就绪。返回 None 表示就绪，否则返回 Err。"""
        if not self._ready:
            return Err(
                SdkError(
                    "OpenCode Adapter not ready (startup not completed or failed)"
                )
            )
        if self._executor is None or self._session_mgr is None:
            return Err(SdkError("OpenCode Adapter internal state invalid"))
        return None

    # ------------------------------------------------------------------
    # 核心执行逻辑（内部方法，被 @llm_tool 方法调用）
    # ------------------------------------------------------------------

    async def _execute_with_retry(
        self,
        prompt: str,
        *,
        cwd: str = "",
        model: str = "",
        variant: str = "",
    ) -> ExecuteResult:
        """执行 OpenCode 任务，支持自动重试。

        重试策略（参考 paperclip opencode-local 的瞬态错误降级）：
        - 首次执行尝试恢复会话（如果存在可恢复的会话）
        - 如果失败且错误可重试（unknown_session / transient_upstream / rate_limit），
          新建会话重试
        - 最多重试 self._config.max_retries 次
        """
        assert self._executor is not None and self._session_mgr is not None

        effective_cwd = cwd or self._config.cwd or os.getcwd()
        signature = compute_prompt_signature(
            instructions_file_path=self._config.instructions_file_path,
            model=self._config.model,
            variant=self._config.variant,
        )

        # 尝试恢复会话
        resume_record = await self._session_mgr.find_resumable(effective_cwd, signature)
        resume_session_id = resume_record.session_id if resume_record else ""

        max_attempts = 1 + max(0, self._config.max_retries)
        last_error: Optional[ClassifiedError] = None

        for attempt in range(max_attempts):
            is_retry = attempt > 0
            if is_retry:
                resume_session_id = ""
                self.logger.info(
                    "Retrying with new session (attempt %d/%d): prev_error=%s",
                    attempt + 1,
                    max_attempts,
                    last_error.kind if last_error else "unknown",
                )

            # 构建 CLI 调用
            invocation, build_err = build_cli_invocation(
                self._config,
                prompt=prompt,
                resume_session_id=resume_session_id,
                cwd=effective_cwd,
                model=model,
                variant=variant,
            )
            if build_err is not None:
                last_error = build_err
                if not is_retryable(build_err.kind):
                    return ExecuteResult(
                        error_kind=build_err.kind,
                        error_message=build_err.message,
                    )
                continue

            # 执行
            parser = OpenCodeOutputParser()
            start_time = time.monotonic()
            stream, exec_err = await self._executor.execute(invocation, parser)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            # 成功
            if exec_err is None:
                session_id = stream.session_id
                is_new_session = not bool(resume_session_id)

                # 更新会话记录
                if session_id:
                    try:
                        await self._session_mgr.upsert(
                            session_id, effective_cwd, signature
                        )
                        # 累计轮次
                        turn_count = len(stream.step_finishes)
                        if turn_count > 0:
                            await self._session_mgr.touch(
                                session_id,
                                turn_count=turn_count,
                            )
                    except Exception as e:
                        self.logger.warning(
                            "Failed to update session record: %s", e
                        )

                result = ExecuteResult(
                    session_id=session_id,
                    is_new_session=is_new_session,
                    final_text=stream.final_text,
                    usage=stream.total_usage,
                    duration_ms=duration_ms,
                    raw_events=[],
                )
                return result

            # 失败 — 记录错误并判断是否重试
            last_error = exec_err

            # 标记会话错误
            if resume_session_id:
                try:
                    await self._session_mgr.mark_error(
                        resume_session_id, exec_err.kind
                    )
                except Exception:
                    pass

            # 不可重试 — 立即返回
            if not is_retryable(exec_err.kind):
                return ExecuteResult(
                    session_id=resume_session_id,
                    error_kind=exec_err.kind,
                    error_message=exec_err.message,
                    retry_not_before=exec_err.retry_not_before,
                    final_text=stream.final_text,
                    duration_ms=duration_ms,
                )

            # 可重试 — 退避后继续下一轮
            is_last_attempt = (attempt + 1) >= max_attempts
            if is_last_attempt:
                self.logger.info("Last attempt failed, skipping backoff")
                break

            if exec_err.retry_not_before:
                wait_sec = _compute_retry_wait_seconds(exec_err.retry_not_before)
                if wait_sec > 0:
                    self.logger.info(
                        "Waiting %ds until retry_not_before=%s",
                        wait_sec,
                        exec_err.retry_not_before,
                    )
                    await asyncio.sleep(wait_sec)
            elif exec_err.kind == TRANSIENT_UPSTREAM:
                backoff = min(2 ** (attempt + 1), 16)
                self.logger.info(
                    "Transient error, backing off %ds before retry", backoff
                )
                await asyncio.sleep(backoff)
            continue

        # 所有重试都失败
        return ExecuteResult(
            error_kind=last_error.kind if last_error else "unknown",
            error_message=last_error.message if last_error else "all retries exhausted",
            retry_not_before=last_error.retry_not_before if last_error else "",
        )

    # ==================================================================
    # LLM 工具集（@llm_tool 装饰器注册）
    # ==================================================================

    @llm_tool(
        name="opencode_execute",
        description=(
            "调用 OpenCode CLI 执行编码任务。OpenCode 是开源的命令行 AI 编码助手，"
            "可以读写文件、运行命令、调试代码、写测试、查文档等。\n\n"
            "适用场景：\n"
            "- 写新功能、新文件\n"
            "- 修改现有代码、修 bug\n"
            "- 运行测试、构建项目\n"
            "- 代码审查、重构\n"
            "- 查阅项目文档、理解代码结构\n\n"
            "参数说明：\n"
            "- prompt: 详细描述要让 OpenCode 做什么。要具体、清晰，包含必要的上下文。\n"
            "- cwd: 工作目录（项目根目录的绝对路径）。同一目录的调用会自动复用会话上下文。\n"
            "- model: 模型 ID（可选）。格式为 provider/model，如 'anthropic/claude-sonnet-4-20250514'。留空使用默认配置。\n"
            "- variant: 推理变体（可选）：'low' / 'medium' / 'high'。留空使用默认配置。\n\n"
            "返回：包含 OpenCode 的最终回复文本、会话 session_id、token 使用量和成本等信息的字典。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "要交给 OpenCode 执行的任务描述。要具体、清晰，包含必要的项目上下文。",
                },
                "cwd": {
                    "type": "string",
                    "description": "工作目录（项目根目录的绝对路径）。同一目录的调用会自动复用会话上下文。留空使用适配器默认配置。",
                },
                "model": {
                    "type": "string",
                    "description": "模型 ID（可选）。格式为 provider/model，如 'anthropic/claude-sonnet-4-20250514'。留空使用默认配置。",
                },
                "variant": {
                    "type": "string",
                    "description": "推理变体（可选）：'low' / 'medium' / 'high'。留空使用默认配置。",
                    "enum": ["", "low", "medium", "high"],
                },
            },
            "required": ["prompt"],
        },
        timeout=300.0,
    )
    async def opencode_execute(
        self,
        prompt: str = "",
        cwd: str = "",
        model: str = "",
        variant: str = "",
        **_,
    ) -> dict[str, Any]:
        """执行 OpenCode 任务。"""
        not_ready = self._ensure_ready()
        if not_ready is not None:
            return not_ready

        if not prompt or not prompt.strip():
            return Err(SdkError("prompt 不能为空"))

        try:
            result = await self._execute_with_retry(
                prompt,
                cwd=cwd,
                model=model,
                variant=variant,
            )
            return Ok(result.to_llm_payload())
        except Exception as e:
            self.logger.exception("opencode_execute failed")
            return Err(SdkError(f"执行失败: {e}"))

    @llm_tool(
        name="opencode_check_health",
        description=(
            "检查 OpenCode CLI 是否可用。返回 CLI 路径、版本信息和适配器状态。\n\n"
            "适用场景：\n"
            "- 在调用 opencode_execute 之前确认环境就绪\n"
            "- 诊断 OpenCode 相关问题\n"
            "- 检查适配器配置是否正确\n\n"
            "返回：包含 cli_available、cli_path、version、config 等信息的字典。"
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        timeout=10.0,
    )
    async def opencode_check_health(self, **_) -> dict[str, Any]:
        """检查 OpenCode CLI 健康状态。"""
        try:
            cli_path = self._config.command or detect_opencode_cli() or ""
            cli_available = bool(cli_path)

            version = ""
            if cli_available:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        cli_path,
                        "--version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    try:
                        stdout, _ = await asyncio.wait_for(
                            proc.communicate(), timeout=5.0
                        )
                        version = stdout.decode("utf-8", errors="replace").strip()
                    except asyncio.TimeoutError:
                        try:
                            proc.kill()
                            await proc.wait()
                        except Exception:
                            pass
                except Exception as e:
                    version = f"(version check failed: {e})"

            return Ok(
                {
                    "cli_available": cli_available,
                    "cli_path": cli_path or "",
                    "version": version,
                    "ready": self._ready,
                    "config": self._config.to_dict(),
                    "sessions_count": len(self._session_mgr._sessions)
                    if self._session_mgr
                    else 0,
                }
            )
        except Exception as e:
            self.logger.exception("opencode_check_health failed")
            return Err(SdkError(f"健康检查失败: {e}"))

    @llm_tool(
        name="opencode_list_sessions",
        description=(
            "列出所有 OpenCode 会话记录。会话按最近使用时间降序排列。\n\n"
            "适用场景：\n"
            "- 查看当前有哪些活跃的 OpenCode 会话\n"
            "- 了解每个会话的工作目录、轮次数、最后错误\n"
            "- 决定是否需要清除某个会话\n\n"
            "返回：包含 sessions 列表的字典，每个会话含 session_id、cwd、turn_count 等字段。"
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        timeout=10.0,
    )
    async def opencode_list_sessions(self, **_) -> dict[str, Any]:
        """列出所有会话。"""
        not_ready = self._ensure_ready()
        if not_ready is not None:
            return not_ready

        try:
            assert self._session_mgr is not None
            records = await self._session_mgr.list_all()
            return Ok(
                {
                    "count": len(records),
                    "sessions": [r.to_dict() for r in records],
                }
            )
        except Exception as e:
            self.logger.exception("opencode_list_sessions failed")
            return Err(SdkError(f"列出会话失败: {e}"))

    @llm_tool(
        name="opencode_clear_session",
        description=(
            "清除 OpenCode 会话记录。\n\n"
            "适用场景：\n"
            "- 会话上下文混乱，想从干净状态开始\n"
            "- 切换到不同的项目分支后清理旧上下文\n"
            "- 会话报错后强制重置\n\n"
            "参数：\n"
            "- cwd: 要清除的工作目录（绝对路径）。留空则清除所有会话。\n\n"
            "返回：包含 cleared_count 的字典。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "cwd": {
                    "type": "string",
                    "description": "要清除的工作目录（绝对路径）。留空则清除所有会话。",
                },
            },
        },
        timeout=10.0,
    )
    async def opencode_clear_session(self, cwd: str = "", **_) -> dict[str, Any]:
        """清除会话记录。"""
        not_ready = self._ensure_ready()
        if not_ready is not None:
            return not_ready

        try:
            assert self._session_mgr is not None
            target = cwd or None
            count = await self._session_mgr.clear(target)
            self.logger.info("Cleared %d session(s) (cwd=%r)", count, target)
            return Ok(
                {
                    "cleared_count": count,
                    "cwd": target or "(all)",
                }
            )
        except Exception as e:
            self.logger.exception("opencode_clear_session failed")
            return Err(SdkError(f"清除会话失败: {e}"))

    @llm_tool(
        name="opencode_get_config",
        description=(
            "获取 OpenCode 适配器的当前配置。\n\n"
            "适用场景：\n"
            "- 了解默认模型、variant、超时、工作目录等设置\n"
            "- 诊断配置问题\n"
            "- 在调用 opencode_execute 前确认参数默认值\n\n"
            "返回：包含完整适配器配置的字典。"
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
        timeout=5.0,
    )
    async def opencode_get_config(self, **_) -> dict[str, Any]:
        """获取适配器配置。"""
        try:
            return Ok(
                {
                    "config": self._config.to_dict(),
                    "ready": self._ready,
                    "default_cwd": self._config.cwd or os.getcwd(),
                }
            )
        except Exception as e:
            return Err(SdkError(f"获取配置失败: {e}"))

    # ==================================================================
    # 插件入口（供 UI / 其他插件调用，非 LLM 工具）
    # ==================================================================

    @plugin_entry(
        id="execute",
        name="执行 OpenCode 任务",
        description="执行 OpenCode 任务（与 opencode_execute LLM 工具相同的功能，供 UI/其他插件调用）。",
        llm_result_fields=["output", "session_id", "usage"],
        input_schema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "任务描述"},
                "cwd": {"type": "string", "description": "工作目录"},
                "model": {"type": "string", "description": "模型 ID"},
                "variant": {"type": "string", "description": "推理变体"},
            },
            "required": ["prompt"],
        },
    )
    async def execute_entry(
        self,
        prompt: str = "",
        cwd: str = "",
        model: str = "",
        variant: str = "",
        **_,
    ) -> Any:
        """插件入口（与 LLM 工具功能相同，供 UI/其他插件调用）。"""
        not_ready = self._ensure_ready()
        if not_ready is not None:
            return not_ready

        if not prompt or not prompt.strip():
            return Err(SdkError("prompt 不能为空"))

        try:
            result = await self._execute_with_retry(
                prompt,
                cwd=cwd,
                model=model,
                variant=variant,
            )
            return Ok(result.to_llm_payload())
        except Exception as e:
            self.logger.exception("execute_entry failed")
            return Err(SdkError(f"执行失败: {e}"))


__all__ = ["OpenCodeAdapterPlugin"]