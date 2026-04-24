# Backend Core

`core/` 是 FastAPI `app/` 与 Celery `worker/` 的共享能力层。

当前阶段已经完成核心服务迁移：配置加载、存储路径、资产 helper、schema 片段、Paper 主链路、Project P0、LLM、MCP、论文下载与 PDF 解析等共享能力已进入 `core/`。
`app/` 只保留 HTTP API、请求/响应 schema、应用生命周期和任务投递入口；`worker/` 后续应只依赖 `core/`，不依赖 `app/`。

## 职责

- 保存两边共享的任务名、数据模型、数据库连接、存储路径与业务服务。
- 避免 `worker/` 依赖 `app/`，保证 Worker 可以独立部署。
- 为后续 ORM、任务契约和服务迁移提供稳定落点。

## 当前状态

- `task_names.py` 已作为任务名契约入口。
- `config.py` 与各 `*_config.py` 已作为 app、worker、脚本共用的配置入口。
- `storage.py`、`assets.py` 与 `schema.py` 已承接共享存储、资产注册与 SQLite schema 能力。
- `services/papers/` 已承接 Paper 主链路，并通过 core DTO 与 API schema 分离。
- `services/projects.py` 已承接 Project P0 的共享业务实现。
- `services/llm/`、`services/mcp/`、`services/paper_download/` 与 `services/pdf_parser/` 已从旧 `app/services/` 迁入。
