from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.services.mcp.zotero_client import zotero_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用生命周期内复用同一个客户端，退出时统一关闭连接。
    app.state.zotero_client = zotero_client
    yield
    await zotero_client.close()


app = FastAPI(
    title="Research-Flow",
    description="面向科研人员的全生命周期研究工作流管理平台",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/services/mcp")
async def mcp_service_status():
    # 返回脱敏后的配置摘要，避免接口中暴露密钥。
    return zotero_client.get_config_summary()


@app.get("/services/mcp/tools")
async def mcp_service_tools():
    tools = await zotero_client.list_tools()
    return {"count": len(tools), "tools": tools}
