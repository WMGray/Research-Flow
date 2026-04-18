from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from agno.tools.mcp import MCPTools
from mcp.client.stdio import StdioServerParameters


# 只展示关键配置名，避免接口或日志中泄漏敏感值。
MANAGED_ENV_KEYS = [
    "PYTHONIOENCODING",
    "PYTHONUTF8",
    "ZOTERO_LOCAL",
    "ZOTERO_API_KEY",
    "ZOTERO_LIBRARY_ID",
    "ZOTERO_LIBRARY_TYPE",
    "UNPAYWALL_EMAIL",
    "UNSAFE_OPERATIONS",
    "ZOTERO_MCP_COMMAND",
    "ZOTERO_MCP_ARGS",
]


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_env_file() -> None:
    """从 backend/.env 读取配置，但不覆盖已经存在的系统环境变量。"""
    env_path = _backend_root() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_optional_bool(name: str, default: bool | None) -> bool | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default

    normalized = raw.strip().lower()
    if normalized in {"auto", "default"}:
        return None
    if normalized in {"1", "true", "yes", "on", "local"}:
        return True
    if normalized in {"0", "false", "no", "off", "web"}:
        return False
    return default


def _get_args(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default

    text = raw.strip()
    if text.startswith("["):
        parsed = json.loads(text)
        return [str(item) for item in parsed]

    return [segment for segment in text.split() if segment]


@dataclass(frozen=True)
class ZoteroMCPSettings:
    """集中保存 Zotero MCP 所需配置，避免散落在业务代码里。"""

    enabled: bool
    command: str
    args: list[str]
    transport: str
    local_mode: bool | None
    api_key: str | None
    library_id: str | None
    library_type: str
    pythonioencoding: str
    pythonutf8: str
    unpaywall_email: str | None
    unsafe_operations: str | None
    timeout_seconds: int


@lru_cache(maxsize=1)
def get_zotero_settings() -> ZoteroMCPSettings:
    """延迟读取配置，便于测试时通过 monkeypatch 覆盖环境变量。"""
    _load_env_file()
    return ZoteroMCPSettings(
        enabled=_get_bool("ZOTERO_MCP_ENABLED", True),
        command=os.getenv("ZOTERO_MCP_COMMAND", "zotero-mcp"),
        args=_get_args("ZOTERO_MCP_ARGS", ["serve"]),
        transport=os.getenv("ZOTERO_MCP_TRANSPORT", "stdio"),
        local_mode=_get_optional_bool("ZOTERO_LOCAL", True),
        api_key=os.getenv("ZOTERO_API_KEY"),
        library_id=os.getenv("ZOTERO_LIBRARY_ID"),
        library_type=os.getenv("ZOTERO_LIBRARY_TYPE", "user"),
        pythonioencoding=os.getenv("PYTHONIOENCODING", "utf-8"),
        pythonutf8=os.getenv("PYTHONUTF8", "1"),
        unpaywall_email=os.getenv("UNPAYWALL_EMAIL"),
        unsafe_operations=os.getenv("UNSAFE_OPERATIONS"),
        timeout_seconds=int(os.getenv("ZOTERO_MCP_TIMEOUT_SECONDS", "60")),
    )


class ZoteroMCPClient:
    """对 Agno 的 MCPTools 做一层轻封装，专门服务于 Zotero MCP。"""

    def __init__(self) -> None:
        self.toolkit: MCPTools | None = None

    def _candidate_command_paths(self) -> list[Path]:
        """优先尝试 uv tool 的标准安装位置，兼容未写入 PATH 的情况。"""
        roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return [
            roaming / "uv" / "tools" / "zotero-mcp-server" / "Scripts" / "zotero-mcp.exe",
            roaming / "uv" / "tools" / "zotero-mcp-server" / "Scripts" / "zotero-mcp",
        ]

    def _resolve_command(self, command: str) -> str:
        """若命令仍是默认值，则自动替换成 uv tool 的绝对路径。"""
        if command != "zotero-mcp":
            return command

        for candidate in self._candidate_command_paths():
            if candidate.exists():
                return str(candidate)

        return command

    def _build_env(self, settings: ZoteroMCPSettings) -> dict[str, str]:
        """把当前进程环境与 Zotero MCP 专属配置合并，避免丢失 PATH 等关键变量。"""
        merged_env = dict(os.environ)
        merged_env["PYTHONIOENCODING"] = settings.pythonioencoding
        merged_env["PYTHONUTF8"] = settings.pythonutf8
        merged_env["ZOTERO_LIBRARY_TYPE"] = settings.library_type

        if settings.local_mode is not None:
            merged_env["ZOTERO_LOCAL"] = "true" if settings.local_mode else "false"
        if settings.api_key:
            merged_env["ZOTERO_API_KEY"] = settings.api_key
        if settings.library_id:
            merged_env["ZOTERO_LIBRARY_ID"] = settings.library_id
        if settings.unpaywall_email:
            merged_env["UNPAYWALL_EMAIL"] = settings.unpaywall_email
        if settings.unsafe_operations:
            merged_env["UNSAFE_OPERATIONS"] = settings.unsafe_operations

        return merged_env

    def _build_server_params(self, settings: ZoteroMCPSettings) -> StdioServerParameters:
        """当前只支持 stdio 方式，便于与 Agno 的 MCPTools 直连。"""
        if settings.transport != "stdio":
            raise ValueError("当前 Zotero MCP 仅支持 stdio 传输模式。")

        env = self._build_env(settings)
        return StdioServerParameters(
            command=self._resolve_command(settings.command),
            args=settings.args,
            env=env,
            encoding=settings.pythonioencoding,
        )

    def reset(self) -> None:
        """测试场景下重置缓存，确保每次都读取最新环境变量。"""
        self.toolkit = None
        get_zotero_settings.cache_clear()

    def get_config_summary(self) -> dict[str, Any]:
        """返回脱敏后的配置摘要，供健康检查或调试接口使用。"""
        settings = get_zotero_settings()
        server_params = self._build_server_params(settings)
        env = server_params.env or {}

        if settings.local_mode is None:
            mode = "auto"
        else:
            mode = "local" if settings.local_mode else "web"

        return {
            "enabled": settings.enabled,
            "framework": "agno",
            "transport": settings.transport,
            "command": server_params.command,
            "args": list(server_params.args),
            "env_keys": [key for key in MANAGED_ENV_KEYS if key in env or key in os.environ],
            "mode": mode,
            "library_id": settings.library_id,
            "timeout_seconds": settings.timeout_seconds,
        }

    async def connect(self) -> MCPTools:
        """建立到 Zotero MCP 的真实连接，并提前加载可用工具列表。"""
        settings = get_zotero_settings()
        if not settings.enabled:
            raise RuntimeError("Zotero MCP 已在环境变量中被禁用。")
        if self.toolkit is not None:
            return self.toolkit

        self.toolkit = MCPTools(
            server_params=self._build_server_params(settings),
            refresh_connection=True,
            timeout_seconds=settings.timeout_seconds,
        )
        await self.toolkit.connect()
        await self.toolkit.build_tools()
        return self.toolkit

    async def list_tools(self) -> list[str]:
        """返回当前已注册到 Agno 的 Zotero MCP 工具名。"""
        toolkit = await self.connect()
        return list(toolkit.functions.keys())

    async def call_zotero_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """直接调用底层 MCP tool，便于后端接口或调试脚本复用。"""
        toolkit = await self.connect()
        if toolkit.session is None:
            raise RuntimeError("Zotero MCP session 尚未初始化。")

        settings = get_zotero_settings()
        result = await toolkit.session.call_tool(
            tool_name,
            arguments or {},
            read_timeout_seconds=timedelta(seconds=settings.timeout_seconds),
        )
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        return result

    async def close(self) -> None:
        """关闭 MCP 连接，避免 FastAPI 生命周期结束后遗留子进程。"""
        if self.toolkit is None:
            return
        await self.toolkit.close()
        self.toolkit = None


zotero_client = ZoteroMCPClient()
