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
├── app/                    # FastAPI 主服务
│   ├── api/                # 接口层：路由定义，只处理 HTTP 请求/响应
│   ├── core/               # 基础层：配置加载、数据库连接、日志初始化
│   ├── models/             # 数据层：SQLAlchemy ORM 表定义
│   ├── schemas/            # 契约层：Pydantic 请求/响应 Schema
│   ├── services/           # 业务层：核心业务逻辑，调用 LLM、处理数据
│   ├── tasks/              # 投递层：向 Celery 队列投递异步任务的入口
│   └── main.py             # FastAPI app 实例，挂载路由，注册生命周期
│
├── worker/                 # Celery 独立包（可单独部署）
│   ├── tasks/              # 任务实现：异步任务与定时任务的具体逻辑
│   ├── app.py              # Celery 实例（celery -A worker.app）
│   ├── config.py           # Celery 配置：Broker、序列化、任务行为等
│   ├── schedules.py        # Beat 调度表：所有 Cron 定义集中管理
│   └── pyproject.toml      # Worker 独立依赖声明
│
├── tests/                  # 测试代码
├── logs/                   # 运行日志（运行时生成，不提交 Git）
├── .env                    # 本地环境变量（不提交 Git）
├── .env.example            # 环境变量配置模板
├── .python-version         # Python 版本锁定
└── pyproject.toml          # 项目元数据 + uv workspace 配置
```

---

## 分层设计

```
HTTP 请求
    │
    ▼
┌─────────────────────────────────────────────────┐
│  app/api/          接口层                         │
│  · 路由定义与参数解析                              │
│  · 调用 Service，返回 Schema                      │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│  app/services/     业务层                         │
│  · 核心业务逻辑                                   │
│  · 调用 LLM、外部 API                             │
│  · 通过 app/tasks/ 投递异步任务                   │
└──────────┬────────────────────────┬─────────────┘
           │                        │
           ▼                        ▼
┌──────────────────┐    ┌──────────────────────────┐
│  app/models/     │    │  worker/tasks/            │
│  数据层           │    │  任务执行层                │
│  · ORM 表定义    │    │  · 异步任务实现             │
│  · 数据库读写    │    │  · 定时任务实现             │
└──────────────────┘    └──────────────────────────┘
```

### app/tasks/ 与 worker/tasks/ 的区别

| | `app/tasks/` | `worker/tasks/` |
|---|---|---|
| **职责** | 投递入口，调用 `.delay()` | 任务的真正实现逻辑 |
| **运行位置** | FastAPI 进程内 | Celery Worker 进程内 |
| **示例** | `analyze_paper.delay(paper_id)` | `@celery.task def analyze_paper(...)` |

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

**独立部署 Worker 时**，只需将 `worker/` 目录打包，安装 `worker/pyproject.toml` 中声明的依赖，无需携带完整的主服务代码。

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