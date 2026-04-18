import asyncio
import sys
from pathlib import Path

# 让脚本可以直接用 `python backend/tests/test_raw_zotero.py` 运行。
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.mcp.zotero_client import zotero_client


async def run_zotero_connection_demo() -> None:
    """最小化的 Zotero MCP 演示脚本。"""
    print("Connecting to Zotero MCP Server using settings from backend/.env ...")

    tools = await zotero_client.list_tools()
    print(f"Loaded {len(tools)} tools")
    print(f"First 10 tools: {tools[:10]}")

    print("\n--- Executing Tool: zotero_search_items ---")
    response = await zotero_client.call_zotero_tool(
        tool_name="zotero_search_items",
        arguments={"query": "machine learning", "limit": 2},
    )

    print(f"\nResponse:\n{response}")
    await zotero_client.close()


if __name__ == "__main__":
    asyncio.run(run_zotero_connection_demo())
