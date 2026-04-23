# 第三方服务清单

本目录用于记录 Research-Flow 后端依赖的外部服务、MCP 连接器与云服务接入方式，重点说明服务定位、配置要求、能力边界与安全约束。

## 当前优先级

- `P0`：`LLM / Agent` 相关配置、模型接入与云服务基础能力
- `P1`：与 `Project`、`Presentation`、`Knowledge` 生成相关的服务接入
- `P2`：`Zotero`、每日推荐抓取等外围接入

## 当前条目

- [zotero-mcp.md](/C:/Users/WMGray/Desktop/Research-Flow/docs/02_backend/services/zotero-mcp.md)
  - `Zotero MCP` 的功能全景与使用说明，覆盖能力介绍、Research-Flow 场景与配置方式。
- [minimax.md](/C:/Users/WMGray/Desktop/Research-Flow/docs/02_backend/services/llm/minimax.md)
  - `MiniMax` 相关说明。
- [aliyun.md](/C:/Users/WMGray/Desktop/Research-Flow/docs/02_backend/services/cloud/aliyun.md)
  - 阿里云相关说明。

## 编写原则

- 服务文档优先回答“为什么接、怎么配、当前支持什么、后续可扩展什么”。
- 凭证、密钥与私有地址不得写入仓库。
- 若服务具备超出当前产品范围的能力，需明确标出当前启用边界。
