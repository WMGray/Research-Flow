# Zotero MCP

## 当前定位

`Zotero MCP` 用于连接用户既有 `Zotero` 文献库，支持浏览条目、读取元数据、识别附件并按需导入到 Research-Flow。

当前优先级为 `P2`，不进入首轮后端实现范围。

## 预期职责

- 浏览 `Zotero` Library 与 Collection
- 读取条目元数据与附件信息
- 将指定条目导入本地 `Paper` 资源
- 建立本地资源与 `Zotero` 条目的映射关系

## 当前边界

- 当前阶段仅保留接口与数据表预留，不要求实现双向同步
- 不要求 `Zotero` 成为主数据源
- 不在本轮后端 `P0 / P1` 开发中优先落地

## 参考资料

- Claude Scholar 的 MCP 配置说明：
  - https://github.com/Galaxy-Dawn/claude-scholar/blob/codex/MCP_SETUP.zh-CN.md
- Zotero MCP 项目仓库：
  - https://github.com/Galaxy-Dawn/zotero-mcp
