# Research-Flow Backend

基于 **FastAPI + Celery** 的科研工作流管理平台后端服务。

## 技术栈

| 类别 | 技术选型 |
|------|---------|
| Web 框架 | FastAPI |
| 包管理 | uv |
| 任务队列 | Celery + Redis |
| LLM / Agent 编排 | Agno |
| 数据库 | SQLite（SQLAlchemy ORM） |
| 数据校验 | Pydantic v2 |
| Python 版本 | 3.13+ |

---

## 目录结构

```
backend/
├── app/                    # FastAPI 入口层
│   ├── api/                # HTTP 路由，只处理请求/响应
│   ├── schemas/            # API 专属 Pydantic 请求/响应 Schema
│   ├── tasks/              # Celery 任务投递入口，只负责发布任务
│   └── main.py             # FastAPI app 实例、路由挂载、生命周期
│
├── worker/                 # Celery 入口层（可独立部署）
│   ├── tasks/              # 任务注册与执行入口，调用 core 中的业务能力
│   ├── app.py              # Celery 实例（celery -A worker.app）
│   ├── config.py           # Celery 配置：Broker、序列化、任务行为等
│   ├── schedules.py        # Beat 调度表：所有 Cron 定义集中管理
│   └── pyproject.toml      # Worker 独立依赖声明
│
├── core/                   # app 与 worker 共享能力层
│   ├── README.md           # 迁移边界与当前状态说明
│   ├── assets.py           # 共享资产注册与文件指纹 helper
│   ├── schema.py           # 共享 SQLite schema 片段
│   ├── storage.py          # 共享存储路径解析
│   ├── task_names.py       # Celery 任务名契约
│   ├── services/           # 新增共享业务服务
│   └── __init__.py
│
├── tests/                  # 测试代码
├── config/                 # 版本化默认配置，不保存密钥
├── data/                   # 运行时数据，只提交目录占位
├── logs/                   # 运行日志（运行时生成，不提交 Git）
├── .env                    # 本地环境变量（不提交 Git）
├── .env.example            # 环境变量配置模板
├── .python-version         # Python 版本锁定
└── pyproject.toml          # 项目元数据 + uv workspace 配置
```

### 当前兼容状态

当前阶段已经完成核心服务迁移：配置加载、存储路径、资产 helper、schema 片段、Paper 主链路、Project P0、LLM、MCP、论文下载与 PDF 解析已进入 `core/`。FastAPI 路由只通过 `core/services` 调用这些共享能力，Worker 后续也应遵循同一边界。

`app/` 当前只保留 HTTP API、请求/响应 schema、应用生命周期和任务投递入口；`core/services/papers/` 已完成 DTO 分离，不再依赖 `app.schemas`。后续目标位置：`core/models/` 承载 ORM，`core/database.py` 承载两边共享的数据库连接。

当前代码与目标文档之间的功能状态、已挂载 API 和 schema 缺口见 [`docs/02_backend/功能状态.md`](../docs/02_backend/功能状态.md)。截至 2026-04-26，Paper / Project / Job 已具备本地 P0 雏形；真实异步队列、完整 Category / Config API、Knowledge / Dataset / Presentation CRUD 仍未完整落地。

---

## 分层设计

```
HTTP 请求 / Celery 消费
    │
    ├───────────────────────────────┐
    ▼                               ▼
┌─────────────────────────────────────────────────┐
│  app/             FastAPI 入口                    │
│  · app/api 处理 HTTP                              │
│  · app/tasks 发布 Celery 任务                      │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  worker/          Celery 入口                     │
│  · worker/tasks 注册任务                          │
│  · worker/schedules 管理定时调度                   │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  core/            共享能力层                       │
│  · models / database / storage                     │
│  · services / task_names                           │
│  · 不依赖 app，供 app 与 worker 共同调用            │
└─────────────────────────────────────────────────┘
```

### app/tasks/ 与 worker/tasks/ 的区别

| | `app/tasks/` | `worker/tasks/` |
|---|---|---|
| **职责** | 投递入口，按 `core/task_names.py` 发布任务 | 任务注册与执行入口 |
| **运行位置** | FastAPI 进程内 | Celery Worker 进程内 |
| **业务逻辑位置** | 不写业务逻辑 | 不写复杂业务逻辑，调用 `core/services` |
| **示例** | `send_task(PAPER_PARSE, kwargs=...)` | `@celery.task(name=PAPER_PARSE)` |

---

## 进程架构

生产环境下由三个独立进程组成：

```
┌─────────────────┐        ┌───────────┐        ┌──────────────────┐
│   FastAPI 主服务  │──投递──▶│   Redis   │──消费──▶│  Celery Worker   │
│   :8000          │        │  Broker   │        │  （可横向扩展）    │
└─────────────────┘        └─────┬─────┘        └──────────────────┘
                                 ▲
                    ┌────────────┘
                    │  定时投递
              ┌─────────────┐
              │ Celery Beat  │
              │ （单实例）    │
              └─────────────┘
```

- **FastAPI**：处理用户请求，投递异步任务
- **Celery Beat**：按 `worker/schedules.py` 中定义的 Cron 定时投递任务，**全局只能运行一个实例**
- **Celery Worker**：消费队列中的任务并执行，可按需启动多个实例

---

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写 LLM API Key 及 Redis 连接地址
```

### 2. 安装依赖

```bash
# 安装主服务依赖
uv sync

# 安装 worker 依赖
uv sync --package research-flow-worker
```

### 3. 启动服务

```bash
# 启动 FastAPI 主服务
uv run uvicorn app.main:app --reload --port 8000

# 启动 Celery Worker
uv run celery -A worker.app worker --loglevel=info

# 启动 Celery Beat（定时调度）
uv run celery -A worker.app beat --loglevel=info
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# API 文档
open http://localhost:8000/docs
```

---

## uv Workspace 说明

本项目使用 uv workspace 管理多包依赖，`worker/` 是一个独立的 Python 包：

```toml
# pyproject.toml（workspace 根）
[tool.uv.workspace]
members = ["worker"]
```

**独立部署 Worker 时**，目标部署包应包含 `worker/` 与 `core/`，不携带 `app/`。Worker 任务实现只能调用 `core/services/` 中的共享业务能力，不能反向依赖 FastAPI schema 或路由。

---

## 环境变量说明

完整配置项见 [`.env.example`](./.env.example)，核心变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_PORT` | 主服务监听端口 | `8000` |
| `DB_PATH` | SQLite 数据库路径 | `./data/research_flow.db` |
| `DEFAULT_LLM_PROVIDER` | 默认 LLM 提供商 | `openai` |
| `DEFAULT_LLM_MODEL` | 默认使用的模型 | `gpt-4o` |
| `CELERY_BROKER_URL` | Redis Broker 地址 | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis 结果存储地址 | `redis://localhost:6379/1` |
| `DAILY_PAPER_PUSH_CRON` | 每日推送 Cron 表达式 | `0 8 * * *` |
