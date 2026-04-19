from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from mcp.client.stdio import StdioServerParameters
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

# 这些键只用于展示当前启用了哪些 MCP 相关配置，
# 不会暴露真实密钥内容，因此可以出现在摘要接口里。
MANAGED_ENV_KEYS = (
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
)


class ZoteroConfig(BaseModel):
    """Zotero MCP 进程的运行时配置模型。"""

    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("ENABLED", "ZOTERO__ENABLED", "ZOTERO_MCP_ENABLED"),
    )
    command: str = Field(
        default="zotero-mcp",
        validation_alias=AliasChoices("COMMAND", "ZOTERO__COMMAND", "ZOTERO_MCP_COMMAND"),
    )
    args: list[str] = Field(
        default_factory=lambda: ["serve"],
        validation_alias=AliasChoices("ARGS", "ZOTERO__ARGS", "ZOTERO_MCP_ARGS"),
    )
    transport: str = Field(
        default="stdio",
        validation_alias=AliasChoices("TRANSPORT", "ZOTERO__TRANSPORT", "ZOTERO_MCP_TRANSPORT"),
    )
    local_mode: Literal["local", "web", "auto"] = Field(
        default="local",
        validation_alias=AliasChoices("LOCAL_MODE", "ZOTERO__LOCAL_MODE", "ZOTERO_LOCAL"),
    )
    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("API_KEY", "ZOTERO__API_KEY", "ZOTERO_API_KEY"),
    )
    library_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LIBRARY_ID", "ZOTERO__LIBRARY_ID", "ZOTERO_LIBRARY_ID"),
    )
    library_type: str = Field(
        default="user",
        validation_alias=AliasChoices("LIBRARY_TYPE", "ZOTERO__LIBRARY_TYPE", "ZOTERO_LIBRARY_TYPE"),
    )
    pythonioencoding: str = Field(
        default="utf-8",
        validation_alias=AliasChoices("PYTHONIOENCODING", "ZOTERO__PYTHONIOENCODING"),
    )
    pythonutf8: str = Field(
        default="1",
        validation_alias=AliasChoices("PYTHONUTF8", "ZOTERO__PYTHONUTF8"),
    )
    unpaywall_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("UNPAYWALL_EMAIL", "ZOTERO__UNPAYWALL_EMAIL"),
    )
    unsafe_operations: str | None = Field(
        default=None,
        validation_alias=AliasChoices("UNSAFE_OPERATIONS", "ZOTERO__UNSAFE_OPERATIONS"),
    )
    timeout_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "TIMEOUT_SECONDS",
            "ZOTERO__TIMEOUT_SECONDS",
            "ZOTERO_MCP_TIMEOUT_SECONDS",
        ),
    )

    @field_validator("args", mode="before")
    @classmethod
    def _parse_args(cls, value: object) -> list[str]:
        if value is None:
            return ["serve"]
        if isinstance(value, str):
            return [segment for segment in value.split() if segment]
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        raise TypeError("zotero args must be a string or list of strings")

    @field_validator("local_mode", mode="before")
    @classmethod
    def _parse_local_mode(cls, value: object) -> Literal["local", "web", "auto"]:
        if value is None:
            return "auto"
        if isinstance(value, bool):
            return "local" if value else "web"

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "local"}:
            return "local"
        if normalized in {"0", "false", "no", "off", "web"}:
            return "web"
        if normalized in {"auto", "default", ""}:
            return "auto"
        raise ValueError("zotero local_mode must be local, web, or auto")

    @field_validator("transport")
    @classmethod
    def _validate_transport(cls, value: str) -> str:
        transport = value.strip().lower()
        if transport != "stdio":
            raise ValueError("zotero transport must be stdio")
        return transport

    @property
    def resolved_command(self) -> str:
        """当命令仍是默认值时，优先解析到 uv tool 的实际安装路径。"""
        if self.command != "zotero-mcp":
            return self.command

        roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        candidates = (
            roaming / "uv" / "tools" / "zotero-mcp-server" / "Scripts" / "zotero-mcp.exe",
            roaming / "uv" / "tools" / "zotero-mcp-server" / "Scripts" / "zotero-mcp",
        )
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return self.command

    def build_env(self) -> dict[str, str]:
        """将当前进程环境与校验后的 Zotero 配置合并为最终启动环境。"""
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = self.pythonioencoding
        env["PYTHONUTF8"] = self.pythonutf8
        env["ZOTERO_LIBRARY_TYPE"] = self.library_type

        if self.local_mode == "local":
            env["ZOTERO_LOCAL"] = "true"
        elif self.local_mode == "web":
            env["ZOTERO_LOCAL"] = "false"

        if self.api_key:
            env["ZOTERO_API_KEY"] = self.api_key
        if self.library_id:
            env["ZOTERO_LIBRARY_ID"] = self.library_id
        if self.unpaywall_email:
            env["UNPAYWALL_EMAIL"] = self.unpaywall_email
        if self.unsafe_operations:
            env["UNSAFE_OPERATIONS"] = self.unsafe_operations

        return env

    def build_server_params(self) -> StdioServerParameters:
        """生成给 MCP client 使用的最终 stdio 启动参数。"""
        return StdioServerParameters(
            command=self.resolved_command,
            args=self.args,
            env=self.build_env(),
            encoding=self.pythonioencoding,
        )

    def summary(self) -> dict[str, object]:
        """返回脱敏后的配置摘要，供健康检查和调试接口使用。"""
        env = self.build_env()
        return {
            "enabled": self.enabled,
            "framework": "agno",
            "transport": self.transport,
            "command": self.resolved_command,
            "args": list(self.args),
            "env_keys": [key for key in MANAGED_ENV_KEYS if key in env or key in os.environ],
            "mode": self.local_mode,
            "library_id": self.library_id,
            "timeout_seconds": self.timeout_seconds,
        }
