from __future__ import annotations

from datetime import timedelta
from typing import Any

from agno.tools.mcp import MCPTools

from app.core.config import get_settings, reset_settings


class ZoteroMCPClient:
    """消费配置层产物并管理 MCP 连接生命周期的轻量客户端。"""

    def __init__(self) -> None:
        # 在应用生命周期内复用同一个 MCPTools 实例，避免每次请求都重复拉起 MCP 子进程。
        self.toolkit: MCPTools | None = None

    def reset(self) -> None:
        # 测试场景会频繁覆盖环境变量，因此需要同时清理，连接缓存和 settings 缓存，避免读到旧配置。
        self.toolkit = None
        reset_settings()

    def get_config_summary(self) -> dict[str, Any]:
        # 这里只透出配置层生成的脱敏摘要，不直接拼接敏感配置。
        return get_settings().zotero.summary()

    async def connect(self) -> MCPTools:
        settings = get_settings().zotero
        if not settings.enabled:
            raise RuntimeError("Zotero MCP is disabled in configuration.")
        if self.toolkit is not None:
            # 如果已经连上，直接复用现有连接。
            return self.toolkit

        # 命令解析和环境变量组装都由配置层负责，client 这里只消费最终生成的 stdio 启动参数。
        self.toolkit = MCPTools(
            server_params=settings.build_server_params(),
            refresh_connection=True,
            timeout_seconds=settings.timeout_seconds,
        )
        # Agno 的 connect() 会吞掉底层连接异常，这里优先走私有 _connect()
        # 以便把 Windows stdio / 子进程握手失败的真实错误直接暴露出来。
        if hasattr(self.toolkit, "_connect"):
            await self.toolkit._connect()  # type: ignore[attr-defined]
        else:
            await self.toolkit.connect()
        if not getattr(self.toolkit, "_initialized", False):
            raise RuntimeError(
                "Zotero MCP 未完成初始化。"
                f" command={settings.resolved_command!r}, args={settings.args!r}"
            )
        return self.toolkit

    async def list_tools(self) -> list[str]:
        # 先确保连接已建立，再读取当前注册的工具列表。
        toolkit = await self.connect()
        return list(toolkit.functions.keys())

    async def call_zotero_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        # 所有 API 和调试调用都复用同一个 session，保持连接行为一致，避免重复初始化。
        toolkit = await self.connect()
        if toolkit.session is None:
            raise RuntimeError("Zotero MCP session is not initialized.")

        settings = get_settings().zotero
        result = await toolkit.session.call_tool(
            tool_name,
            arguments or {},
            read_timeout_seconds=timedelta(seconds=settings.timeout_seconds),
        )
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        return result

    async def close(self) -> None:
        # 在 FastAPI 生命周期结束时主动关闭 MCP 子进程，避免留下悬挂连接。
        if self.toolkit is None:
            return
        await self.toolkit.close()
        self.toolkit = None


zotero_client = ZoteroMCPClient()
