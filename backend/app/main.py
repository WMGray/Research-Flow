"""Research-Flow FastAPI 应用入口。

本文件负责创建应用实例、注册生命周期和挂载各业务路由。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.jobs import router as jobs_router
from app.api.paper_download import router as paper_download_router
from app.api.papers import router as papers_router
from app.api.projects import router as projects_router
from app.api.resources import router as resources_router
from core.services.mcp.zotero_client import zotero_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用生命周期内复用的外部客户端资源。"""

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

app.include_router(paper_download_router)
app.include_router(papers_router)
app.include_router(projects_router)
app.include_router(resources_router)
app.include_router(jobs_router)


@app.get("/health")
async def health_check():
    """返回服务健康状态。"""

    return {"status": "ok"}


@app.get("/services/mcp")
async def mcp_service_status():
    """返回 MCP 服务的脱敏配置摘要。"""

    # 返回脱敏后的配置摘要，避免接口中暴露密钥。
    return zotero_client.get_config_summary()


@app.get("/services/mcp/tools")
async def mcp_service_tools():
    """列出当前 MCP 服务暴露的工具。"""

    tools = await zotero_client.list_tools()
    return {"count": len(tools), "tools": tools}
