# Research-Flow

> 面向科研人员的全生命周期研究工作流管理平台

## 简介

Research-Flow 覆盖从文献调研到论文录用的完整科研流程，通过自动化辅助与人工审核相结合，降低科研管理成本，提升研究效率。

**核心工作流**

```
文献调研分析 → 科研进展追踪 → 实验规划 → 实验结果分析 → 论文写作 → 投稿/Rebuttal → 录用后处理
```

## 主要功能

- **文献管理** — 批量/单篇入库，自动生成结构化分析文档，保留独立人工笔记空间
- **文献调研** — 根据关键词/领域自动抓取相关论文，支持预览、筛选并批量纳入文献管理
- **每日推送** — 定时抓取 `Arxiv` 最新论文，自动评分，快速筛选入库
- **数据集管理** — 独立数据集档案，与论文形成关联，支持实验结果横向对比
- **科研进展追踪（课题管理）** — 以 Related Work / Method / Experiment / Conclusion 四模块管理课题全生命周期
- **实验规划** — 汇总当前课题相关论文的实验设置，结合课题中的 Related Work 生成实验建议
- **论文写作** — 基于课题积累逐章节辅助生成初稿
- **投稿 & Rebuttal** — 格式检查、审稿意见逐条回复辅助
- **会议追踪** — 集中管理投稿截止、审稿通知等关键时间节点
- **知识图谱** — 论文、数据集、课题三类关系可视化

---

## 技术栈

| 层 | 技术选型 |
|----|---------|
| 前端框架 | React 19 + TypeScript 5.7 + Vite 6 |
| 前端状态 | Zustand 5 + TanStack Query 5 |
| 前端路由 | React Router 7 |
| 后端框架 | FastAPI + Python 3.13 |
| 包管理 | uv（含 workspace 多包支持） |
| 任务队列 | Celery 5 + Redis |
| 数据库 | SQLite（SQLAlchemy ORM） |

---

## 项目结构

```
Research-Flow/
├── backend/                # Python 后端服务
│   ├── app/                #   FastAPI 主服务（接口、业务、模型等分层）
│   ├── worker/             #   Celery Worker 独立包（异步任务 + 定时调度）
│   ├── tests/              #   测试代码
│   ├── logs/               #   运行日志（运行时生成）
│   ├── .env.example        #   环境变量配置模板
│   └── pyproject.toml      #   uv workspace 根配置
│
├── frontend/               # Web 前端应用
│   ├── src/                #   应用源码（api / components / features 等）
│   ├── public/             #   静态资源
│   ├── .env.example        #   环境变量配置模板
│   └── package.json
│
├── docs/                   # 项目文档
├── scripts/                # 工程脚本（初始化、迁移等）
├── .gitignore
├── .editorconfig
├── Makefile                # 常用命令入口
└── README.md
```

> 详细说明见各子目录 README：[backend](./backend/README.md) · [frontend](./frontend/README.md)

---

## 环境要求

| 依赖 | 版本要求 |
|------|---------|
| Python | >= 3.13 |
| uv | 最新版 |
| Node.js | >= 18 |
| Redis | >= 7（运行 Celery 时需要） |

---

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd Research-Flow
```

### 2. 配置环境变量

```bash
# 后端：复制模板并填入 LLM API Key、Redis 地址等
cp backend/.env.example backend/.env

# 前端：按需修改后端 API 地址（默认 http://localhost:8000）
cp frontend/.env.example frontend/.env
```

### 3. 安装依赖

```bash
make install
```

### 4. 启动开发环境

**一键启动前后端（不含 Celery）：**

```bash
make dev
```

**按需分别启动各进程：**

```bash
# FastAPI 主服务
make dev-backend

# Celery Worker（执行异步任务）
uv run celery -A worker.app worker --loglevel=info

# Celery Beat（定时任务调度，全局只能运行一个实例）
uv run celery -A worker.app beat --loglevel=info

# 前端开发服务
make dev-frontend
```

### 5. 验证

| 服务 | 地址 |
|------|------|
| 前端应用 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档（Swagger） | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

---

## 常用命令

```bash
make init        # 首次初始化（安装依赖 + 生成 .env）
make dev         # 同时启动前后端开发服务
make install     # 安装前后端全部依赖
make lint        # 检查前后端代码风格
make fmt         # 格式化前后端代码
make clean       # 清理构建产物与缓存
```

---

## 开发文档

| 目录 | 说明 |
|------|------|
| [`docs/00_overview/`](./docs/00_overview/) | 项目背景与用户需求文档 |
| [`docs/01_frontend/`](./docs/01_frontend/) | 前端设计文档 |
| [`docs/02_backend/`](./docs/02_backend/) | 后端架构文档 |
| [`docs/03_api/`](./docs/03_api/) | API 接口文档 |
| [`docs/04_reference/`](./docs/04_reference/) | 参考资料 |

---

## License

MIT
