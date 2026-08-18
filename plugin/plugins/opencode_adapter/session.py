"""OpenCode Adapter — 会话管理器。

负责：
1. 维护 cwd → SessionRecord 的映射
2. 判断是否可以恢复会话（cwd 匹配 + 提示包签名匹配）
3. 通过 PluginStore 持久化会话记录
4. 标记会话为损坏以便下次跳过

设计要点：
- 使用 PluginStore 而非独立 SQLite，符合 SDK 设计
- 提示包签名用于检测 instructions 文件 / 模型 / variant 变化
- 线程安全由 asyncio.Lock 保证（插件运行在单事件循环）
- 与 Cursor 适配器的 SessionManager 结构对齐，但签名计算
  基于 OpenCode 特有的字段（instructions_file_path / model / variant）
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any, Optional

from .models import SessionRecord


# ---------------------------------------------------------------------------
# 提示包签名
# ---------------------------------------------------------------------------


def compute_prompt_signature(
    *,
    instructions_file_path: str = "",
    model: str = "",
    variant: str = "",
    extra: str = "",
) -> str:
    """计算提示包签名。

    签名基于影响 OpenCode CLI 上下文构建的"环境"因素：
    - instructions 文件路径
    - 默认模型
    - 推理变体
    - 额外标记

    当任一变化时，签名变化，旧会话会被放弃。
    """
    parts = [
        f"instructions:{instructions_file_path or ''}",
        f"model:{model or ''}",
        f"variant:{variant or ''}",
        f"extra:{extra or ''}",
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 会话管理器
# ---------------------------------------------------------------------------


class SessionManager:
    """会话管理器。

    会话记录通过 PluginStore 持久化，key 格式为
    ``opencode_session:{cwd}``，其中 cwd 是工作目录的绝对路径。
    """

    STORE_KEY_PREFIX = "opencode_session:"

    def __init__(self, store: Any, logger: Any = None) -> None:
        self.store = store
        self.logger = logger
        self._lock = asyncio.Lock()
        self._sessions: dict[str, SessionRecord] = {}
        """key = cwd（绝对路径），value = SessionRecord。"""

    def __len__(self) -> int:
        return len(self._sessions)

    # ------------------------------------------------------------------
    # 加载 / 保存
    # ------------------------------------------------------------------

    async def load(self) -> None:
        """从 PluginStore 加载所有会话记录。"""
        async with self._lock:
            self._sessions.clear()
            try:
                result = await self.store.keys(prefix=self.STORE_KEY_PREFIX)
                keys = _unwrap_result(result, default=[])
                for key in keys:
                    if not isinstance(key, str):
                        continue
                    get_result = await self.store.get(key)
                    data = _unwrap_result(get_result, default=None)
                    if isinstance(data, dict):
                        try:
                            record = SessionRecord.from_dict(data)
                            self._sessions[record.cwd] = record
                        except Exception as e:
                            if self.logger is not None:
                                try:
                                    self.logger.warning(
                                        "Failed to load session %s: %s", key, e
                                    )
                                except Exception:
                                    pass
            except Exception as e:
                if self.logger is not None:
                    try:
                        self.logger.warning("SessionManager.load failed: %s", e)
                    except Exception:
                        pass

        if self.logger is not None:
            try:
                self.logger.info(
                    "SessionManager loaded %d sessions", len(self._sessions)
                )
            except Exception:
                pass

    async def _persist(self, cwd: str, record: SessionRecord) -> None:
        """持久化单条记录。"""
        key = self._key(cwd)
        try:
            await self.store.set(key, record.to_dict())
        except Exception as e:
            if self.logger is not None:
                try:
                    self.logger.warning("Failed to persist session %s: %s", key, e)
                except Exception:
                    pass

    async def _delete(self, cwd: str) -> None:
        """删除单条记录。"""
        key = self._key(cwd)
        try:
            await self.store.delete(key)
        except Exception as e:
            if self.logger is not None:
                try:
                    self.logger.warning("Failed to delete session %s: %s", key, e)
                except Exception:
                    pass

    def _key(self, cwd: str) -> str:
        return f"{self.STORE_KEY_PREFIX}{cwd}"

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def find_resumable(
        self,
        cwd: str,
        prompt_signature: str,
    ) -> Optional[SessionRecord]:
        """查找可恢复的会话。

        可恢复的条件：
        1. cwd 匹配
        2. prompt_signature 匹配（提示包未变化）
        3. last_error 不是不可恢复的错误（unknown_session / auth_error）
        4. session_id 非空
        """
        async with self._lock:
            record = self._sessions.get(cwd)
            if record is None:
                return None
            if not record.session_id:
                return None
            if record.prompt_signature != prompt_signature:
                return None
            if record.last_error in ("unknown_session", "auth_error", "provider_unavailable", "model_not_available"):
                return None
            return record

    async def list_all(self) -> list[SessionRecord]:
        """返回所有会话记录（按 last_used_at 降序）。"""
        async with self._lock:
            records = list(self._sessions.values())
        records.sort(key=lambda r: r.last_used_at, reverse=True)
        return records

    # ------------------------------------------------------------------
    # 更新
    # ------------------------------------------------------------------

    async def upsert(
        self,
        session_id: str,
        cwd: str,
        prompt_signature: str,
    ) -> SessionRecord:
        """新建或更新会话记录。"""
        now = time.time()
        async with self._lock:
            existing = self._sessions.get(cwd)
            if existing is not None and existing.session_id == session_id:
                existing.last_used_at = now
                await self._persist(cwd, existing)
                return existing

            record = SessionRecord(
                session_id=session_id,
                cwd=cwd,
                prompt_signature=prompt_signature,
                created_at=existing.created_at if existing is not None else now,
                last_used_at=now,
                turn_count=existing.turn_count if existing is not None else 0,
                last_error="",
            )
            self._sessions[cwd] = record
            await self._persist(cwd, record)
            return record

    async def touch(
        self,
        session_id: str,
        *,
        turn_count: int = 0,
    ) -> None:
        """更新会话的最近使用时间和轮次。"""
        async with self._lock:
            for record in self._sessions.values():
                if record.session_id == session_id:
                    record.last_used_at = time.time()
                    if turn_count > 0:
                        record.turn_count += turn_count
                    await self._persist(record.cwd, record)
                    return

    async def mark_error(
        self,
        session_id: str,
        error_kind: str,
    ) -> None:
        """标记会话的最近错误。"""
        async with self._lock:
            for record in self._sessions.values():
                if record.session_id == session_id:
                    record.last_error = error_kind
                    await self._persist(record.cwd, record)
                    return

    async def clear(self, cwd: Optional[str] = None) -> int:
        """清除会话记录。"""
        async with self._lock:
            if cwd is not None:
                if cwd in self._sessions:
                    del self._sessions[cwd]
                    await self._delete(cwd)
                    return 1
                return 0

            count = len(self._sessions)
            keys_to_delete = list(self._sessions.keys())
            self._sessions.clear()
            for k in keys_to_delete:
                await self._delete(k)
            return count


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _unwrap_result(result: Any, default: Any = None) -> Any:
    """解包 Result 类型。"""
    if result is None:
        return default
    value_or_none = getattr(result, "value_or_none", None)
    if callable(value_or_none):
        try:
            value = value_or_none()
            return value if value is not None else default
        except Exception:
            return default
    is_ok = getattr(result, "is_ok", None)
    if callable(is_ok):
        try:
            if result.is_ok():
                value = getattr(result, "value", default)
                return value if value is not None else default
            return default
        except Exception:
            return default
    return result


__all__ = [
    "compute_prompt_signature",
    "SessionManager",
]