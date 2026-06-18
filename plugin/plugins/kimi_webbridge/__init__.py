"""
Kimi WebBridge 浏览器自动化插件
通过Kimi WebBridge守护进程控制用户真实浏览器（保留登录会话）。
守护进程地址: http://127.0.0.1:10086

核心概念:
- 一个任务 = 一个session = 一个标签组
- snapshot返回的@e引用可直接用于click/fill，比CSS选择器更稳定
- 你可以连续调用多个工具完成复杂任务：navigate → snapshot → click/fill
"""

import asyncio
import json
import subprocess
import tempfile
import os
import random
import string
from typing import Any, Optional
from pathlib import Path

from plugin.sdk.plugin import (
    NekoPluginBase, neko_plugin, llm_tool, lifecycle,
    Ok, Err, SdkError,
)


@neko_plugin
class KimiWebBridgePlugin(NekoPluginBase):
    """Kimi WebBridge 浏览器自动化插件"""

    DAEMON_URL = "http://127.0.0.1:10086"

    def __init__(self, ctx: Any):
        super().__init__(ctx)
        self.sessions = {}
        self.daemon_running = False
        self.webbridge_path = self._find_webbridge_path()

    def _find_webbridge_path(self) -> Optional[Path]:
        if os.name == 'nt':
            path = Path.home() / ".kimi-webbridge" / "bin" / "kimi-webbridge.exe"
        else:
            path = Path.home() / ".kimi-webbridge" / "bin" / "kimi-webbridge"
        return path if path.exists() else None

    @lifecycle(id="startup")
    async def on_startup(self, **_):
        self.logger.info("Kimi WebBridge 插件启动中...")
        if not self.webbridge_path:
            self.logger.warning("未找到Kimi WebBridge，请先安装")
            return Ok({"status": "warning", "message": "Kimi WebBridge未安装"})
        self.daemon_running = await self._check_daemon_alive()
        if not self.daemon_running:
            self.logger.info("守护进程未运行，尝试启动...")
            await self._start_daemon()
        else:
            self.logger.info("Kimi WebBridge守护进程已运行")
        return Ok({"status": "ready", "webbridge_installed": bool(self.webbridge_path), "daemon_running": self.daemon_running})

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        self.logger.info("Kimi WebBridge 插件关闭中...")
        return Ok({"status": "stopped"})

    async def _run_daemon_command(self, args: list) -> subprocess.CompletedProcess:
        if not self.webbridge_path:
            raise SdkError("Kimi WebBridge未安装")
        cmd = [str(self.webbridge_path)] + args
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return subprocess.CompletedProcess(
            args=cmd, returncode=process.returncode,
            stdout=stdout.decode('utf-8') if stdout else '',
            stderr=stderr.decode('utf-8') if stderr else ''
        )

    async def _check_daemon_alive(self) -> bool:
        try:
            process = await asyncio.create_subprocess_exec(
                "curl.exe", "-s", "-o", "NUL", "-w", "%{http_code}",
                f"{self.DAEMON_URL}/command",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            code = stdout.decode('utf-8').strip()
            return code in ("200", "405")
        except Exception:
            return False

    async def _start_daemon(self):
        try:
            self.logger.info("正在启动Kimi WebBridge守护进程...")
            pid_file = Path.home() / ".kimi-webbridge" / "daemon.pid"
            if pid_file.exists():
                try: pid_file.unlink()
                except Exception: pass
            await self._run_daemon_command(["start"])
            for _ in range(8):
                await asyncio.sleep(1.0)
                if await self._check_daemon_alive():
                    self.daemon_running = True
                    self.logger.info("Kimi WebBridge守护进程启动成功")
                    return
            self.logger.error("守护进程启动超时")
        except Exception as e:
            self.logger.error(f"启动守护进程异常: {e}")

    def _rand_suffix(self) -> str:
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    async def _ensure_daemon(self):
        if self.daemon_running and await self._check_daemon_alive():
            return
        await self._start_daemon()

    async def _execute_action(self, action: str, args: dict, session: str) -> dict:
        await self._ensure_daemon()
        request_data = {"action": action, "args": args, "session": session}
        body = json.dumps(request_data, ensure_ascii=False)
        tmp_name = f"webbridge-req-{self._rand_suffix()}.json"
        tmp_path = os.path.join(tempfile.gettempdir(), tmp_name)
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(body)
            curl_cmd = [
                "curl.exe", "-s", "-X", "POST",
                f"{self.DAEMON_URL}/command",
                "-H", "Content-Type: application/json",
                "--data-binary", f"@{tmp_path}"
            ]
            process = await asyncio.create_subprocess_exec(
                *curl_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode('utf-8') if stdout else ''
            if process.returncode == 0 and stdout_str.strip():
                return json.loads(stdout_str)
            self.daemon_running = False
            await self._start_daemon()
            await asyncio.sleep(1.0)
            p2 = await asyncio.create_subprocess_exec(
                *curl_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            s2, _ = await p2.communicate()
            s2_str = s2.decode('utf-8') if s2 else ''
            if p2.returncode == 0 and s2_str.strip():
                return json.loads(s2_str)
            return {"ok": False, "error": {"code": "failed", "message": "守护进程无响应，请确认Kimi浏览器扩展已安装并连接"}}
        except Exception as e:
            return {"ok": False, "error": {"code": "exception", "message": str(e)}}
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # ═══════════════════════════════════════════════════════════════════════
    # LLM Tools - 这些工具会注册给LLM，猫娘可以通过function calling调用
    # ═══════════════════════════════════════════════════════════════════════

    @llm_tool(
        name="webbridge_navigate",
        description=(
            "在浏览器中导航到指定URL。首次调用打开新标签页。\n"
            "你可以连续调用多个工具完成复杂任务！例如：navigate打开页面→snapshot读取→click点击→fill填写。\n"
            "session标识当前任务，同一任务所有命令用相同session名。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要导航到的完整URL"},
                "new_tab": {"type": "boolean", "description": "是否在新标签页中打开（默认true）"},
                "group_title": {"type": "string", "description": "标签组标题（第一次navigate时用用户语言设置）"},
                "session": {"type": "string", "description": "会话ID（同一任务用同一session名）"}
            },
            "required": ["url"]
        }
    )
    async def webbridge_navigate(self, *, url: str, new_tab: bool = True, group_title: str = None, session: str = "webbridge-session", **_):
        if not url:
            return {"error": "URL不能为空"}
        if session not in self.sessions:
            self.sessions[session] = {"tabs": []}
        args = {"url": url, "newTab": new_tab}
        if group_title:
            args["group_title"] = group_title
        result = await self._execute_action("navigate", args, session)
        if result.get("ok"):
            data = result.get("data", result)
            self.sessions[session]["tabs"].append(data)
            return {"success": True, "url": url, "tab_id": data.get("tabId"), "message": "导航成功，可以继续操作页面"}
        return {"error": f"导航失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_snapshot",
        description=(
            "获取当前页面的可访问性树快照，用于理解页面结构和定位元素。\n"
            "返回的tree中每个交互元素带有@e引用（如@e123），可直接用于后续的click和fill。\n"
            "这是多步操作的关键步骤：navigate→snapshot(读取页面)→click/fill(操作页面)。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "session": {"type": "string", "description": "会话ID"}
            }
        }
    )
    async def webbridge_snapshot(self, *, session: str = "webbridge-session", **_):
        result = await self._execute_action("snapshot", {}, session)
        if result.get("ok"):
            data = result.get("data", result)
            return {"success": True, "url": data.get("url"), "title": data.get("title"), "tree": data.get("tree")}
        return {"error": f"获取快照失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_click",
        description=(
            "点击页面中的元素。selector可以是snapshot返回的@e引用（如@e123）或CSS选择器。\n"
            "优先使用@e引用，比CSS选择器更稳定。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "元素选择器（@e引用如@e123，或CSS选择器）"},
                "session": {"type": "string", "description": "会话ID"}
            },
            "required": ["selector"]
        }
    )
    async def webbridge_click(self, *, selector: str, session: str = "webbridge-session", **_):
        if not selector:
            return {"error": "选择器不能为空"}
        result = await self._execute_action("click", {"selector": selector}, session)
        if result.get("ok"):
            data = result.get("data", result)
            return {"success": True, "tag": data.get("tag"), "text": data.get("text"), "message": "点击成功"}
        return {"error": f"点击失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_fill",
        description=(
            "填写表单输入框。selector可以是@e引用或CSS选择器。\n"
            "支持<input>/<textarea>和[contenteditable]富文本编辑器。\n"
            "fill是清除并插入模式：已有内容会被替换。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "输入框选择器（@e引用或CSS选择器）"},
                "value": {"type": "string", "description": "要填写的值"},
                "session": {"type": "string", "description": "会话ID"}
            },
            "required": ["selector", "value"]
        }
    )
    async def webbridge_fill(self, *, selector: str, value: str, session: str = "webbridge-session", **_):
        if not selector:
            return {"error": "选择器不能为空"}
        result = await self._execute_action("fill", {"selector": selector, "value": value}, session)
        if result.get("ok"):
            data = result.get("data", result)
            return {"success": True, "tag": data.get("tag"), "mode": data.get("mode"), "message": "填写成功"}
        return {"error": f"填写失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_evaluate",
        description=(
            "在当前页面执行JavaScript代码（支持async/await）。\n"
            "用紧凑的JSON.stringify(data)，不要用null,2格式化。\n"
            "两次调用间重复声明同一个const/let会抛SyntaxError，用IIFE包装。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "要执行的JavaScript代码"},
                "session": {"type": "string", "description": "会话ID"}
            },
            "required": ["code"]
        }
    )
    async def webbridge_evaluate(self, *, code: str, session: str = "webbridge-session", **_):
        if not code:
            return {"error": "JavaScript代码不能为空"}
        result = await self._execute_action("evaluate", {"code": code}, session)
        if result.get("ok"):
            data = result.get("data", result)
            return {"success": True, "type": data.get("type"), "value": data.get("value")}
        return {"error": f"执行JavaScript失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_screenshot",
        description=(
            "对当前页面截图。守护进程将图片写入磁盘并返回文件路径。\n"
            "返回 {format, path, sizeBytes, mimeType}。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "format": {"type": "string", "description": "截图格式（png或jpeg）", "enum": ["png", "jpeg"]},
                "quality": {"type": "integer", "description": "JPEG质量0-100"},
                "selector": {"type": "string", "description": "元素选择器（可选）"},
                "path": {"type": "string", "description": "保存路径（可选）"},
                "session": {"type": "string", "description": "会话ID"}
            }
        }
    )
    async def webbridge_screenshot(self, *, format: str = "png", quality: int = 80, selector: str = None, path: str = None, session: str = "webbridge-session", **_):
        args = {"format": format, "quality": quality}
        if selector: args["selector"] = selector
        if path: args["path"] = path
        result = await self._execute_action("screenshot", args, session)
        if result.get("ok"):
            data = result.get("data", result)
            return {"success": True, "format": data.get("format"), "path": data.get("path"), "size_bytes": data.get("sizeBytes")}
        return {"error": f"截图失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_list_tabs",
        description="列出当前会话中的所有标签页。返回 {tabs:[{tabId, url, title, active}]}。",
        parameters={"type": "object", "properties": {"session": {"type": "string", "description": "会话ID"}}}
    )
    async def webbridge_list_tabs(self, *, session: str = "webbridge-session", **_):
        result = await self._execute_action("list_tabs", {}, session)
        if result.get("ok"):
            data = result.get("data", result)
            return {"success": True, "tabs": data.get("tabs", [])}
        return {"error": f"列出标签页失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_find_tab",
        description="选择一个已打开的标签页作为当前操作标签页。传入完整URL。active=true选择用户当前查看的标签页。",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要查找的标签页URL"},
                "active": {"type": "boolean", "description": "是否选择用户当前查看的标签页"},
                "session": {"type": "string", "description": "会话ID"}
            },
            "required": ["url"]
        }
    )
    async def webbridge_find_tab(self, *, url: str, active: bool = False, session: str = "webbridge-session", **_):
        if not url:
            return {"error": "URL不能为空"}
        result = await self._execute_action("find_tab", {"url": url, "active": active}, session)
        if result.get("ok"):
            data = result.get("data", result)
            return {"success": True, "url": data.get("url", url), "tab_id": data.get("tabId")}
        return {"error": f"查找标签页失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_close_tab",
        description="关闭当前会话中的当前标签页。",
        parameters={"type": "object", "properties": {"session": {"type": "string", "description": "会话ID"}}}
    )
    async def webbridge_close_tab(self, *, session: str = "webbridge-session", **_):
        result = await self._execute_action("close_tab", {}, session)
        if result.get("ok"):
            return {"success": True, "message": "标签页已关闭"}
        return {"error": f"关闭标签页失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_close_session",
        description="关闭当前会话的所有标签页。如果用户可能继续跟进，先给出答案再关闭。",
        parameters={"type": "object", "properties": {"session": {"type": "string", "description": "会话ID"}}}
    )
    async def webbridge_close_session(self, *, session: str = "webbridge-session", **_):
        result = await self._execute_action("close_session", {}, session)
        if result.get("ok"):
            data = result.get("data", result)
            if session in self.sessions:
                del self.sessions[session]
            return {"success": True, "closed": data.get("closed", 0), "message": f"已关闭{data.get('closed', 0)}个标签页"}
        return {"error": f"关闭会话失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_upload",
        description="向文件输入框上传文件。",
        parameters={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "文件输入框选择器"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "文件路径数组"},
                "session": {"type": "string", "description": "会话ID"}
            },
            "required": ["selector", "files"]
        }
    )
    async def webbridge_upload(self, *, selector: str, files: list, session: str = "webbridge-session", **_):
        result = await self._execute_action("upload", {"selector": selector, "files": files}, session)
        if result.get("ok"):
            data = result.get("data", result)
            return {"success": True, "file_count": data.get("fileCount")}
        return {"error": f"上传失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_save_as_pdf",
        description="将当前页面渲染为PDF并返回文件路径。",
        parameters={
            "type": "object",
            "properties": {
                "paper_format": {"type": "string", "description": "纸张格式", "enum": ["letter", "a4", "legal", "a3", "tabloid"]},
                "landscape": {"type": "boolean", "description": "横向"},
                "scale": {"type": "number", "description": "缩放比例0.1-2.0"},
                "path": {"type": "string", "description": "输出路径（可选）"},
                "session": {"type": "string", "description": "会话ID"}
            }
        }
    )
    async def webbridge_save_as_pdf(self, *, paper_format: str = "letter", landscape: bool = False, scale: float = 1.0, path: str = None, session: str = "webbridge-session", **_):
        args = {"paper_format": paper_format, "landscape": landscape, "scale": scale, "print_background": True}
        if path: args["path"] = path
        result = await self._execute_action("save_as_pdf", args, session)
        if result.get("ok"):
            data = result.get("data", result)
            return {"success": True, "path": data.get("path"), "size_bytes": data.get("sizeBytes")}
        return {"error": f"保存PDF失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_network",
        description="监控/查看浏览器网络请求。cmd: start/stop/list/detail。",
        parameters={
            "type": "object",
            "properties": {
                "cmd": {"type": "string", "description": "操作命令", "enum": ["start", "stop", "list", "detail"]},
                "filter": {"type": "string", "description": "过滤条件"},
                "requestId": {"type": "string", "description": "请求ID（detail时使用）"},
                "session": {"type": "string", "description": "会话ID"}
            },
            "required": ["cmd"]
        }
    )
    async def webbridge_network(self, *, cmd: str, filter: str = None, requestId: str = None, session: str = "webbridge-session", **_):
        args = {"cmd": cmd}
        if filter: args["filter"] = filter
        if requestId: args["requestId"] = requestId
        result = await self._execute_action("network", args, session)
        if result.get("ok"):
            return {"success": True, "data": result.get("data", result)}
        return {"error": f"网络操作失败: {result.get('error', {}).get('message', '未知错误')}"}

    @llm_tool(
        name="webbridge_cdp",
        description="Raw chrome.debugger passthrough。低级逃生舱，用于上述工具无法覆盖的场景。",
        parameters={
            "type": "object",
            "properties": {
                "method": {"type": "string", "description": "CDP方法名"},
                "params": {"type": "object", "description": "CDP方法参数"},
                "session": {"type": "string", "description": "会话ID"}
            },
            "required": ["method"]
        }
    )
    async def webbridge_cdp(self, *, method: str, params: dict = None, session: str = "webbridge-session", **_):
        args = {"method": method}
        if params: args["params"] = params
        result = await self._execute_action("cdp", args, session)
        if result.get("ok"):
            return {"success": True, "data": result.get("data", result)}
        return {"error": f"CDP操作失败: {result.get('error', {}).get('message', '未知错误')}"}
