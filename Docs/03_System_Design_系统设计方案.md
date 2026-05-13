# PaperFlow 系统设计方案

## 1. 架构目标

系统架构需要满足以下目标：

1. 本地优先。
2. 前后端分离。
3. 文件与数据库协同。
4. 后台任务可恢复。
5. Obsidian 导出友好。
6. 后续可封装为桌面软件。

## 2. 推荐架构

```text
┌─────────────────────────────────────────────┐
│ Frontend                                    │
│ React / Vue                                 │
│ Dashboard / Table / Detail / Review UI      │
└──────────────────────┬──────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────┐
│ Backend                                      │
│ FastAPI                                      │
│ API / Service / Task Controller              │
└──────────┬────────────┬────────────┬─────────┘
           │            │            │
┌──────────▼───┐ ┌──────▼──────┐ ┌───▼─────────┐
│ SQLite       │ │ File Store  │ │ Worker      │
│ Metadata     │ │ PDF/MD/IMG  │ │ Parse/LLM   │
└──────────────┘ └─────────────┘ └─────────────┘
```

## 3. 模块划分

| 模块 | 职责 |
|---|---|
| Paper Service | Paper 元数据、状态、路径、查询 |
| Search Service | Search Batch、Candidate、Gate 1 |
| Acquire Service | PDF 检查、解析任务、Gate 2 |
| Library Service | 正式论文库、聚合、阅读状态 |
| Project Service | 课题、方向、关联论文 |
| File Service | 文件复制、移动、路径检查、冲突处理 |
| Export Service | Obsidian Markdown 和目录导出 |
| Task Service | 任务创建、执行、重试、日志 |
| LLM Service | 分类建议、note 生成、摘要生成 |
| Settings Service | workspace、模型、API key、路径配置 |

## 4. 技术选型

### 4.1 后端

推荐：

```text
FastAPI
SQLModel 或 SQLAlchemy
Pydantic
SQLite
Uvicorn
```

原因：

1. Python 生态适合 PDF 解析和 LLM 调用。
2. FastAPI 适合本地 Web 和后续桌面封装。
3. SQLite 足够支持个人科研工作台。
4. Pydantic 便于定义 schema。

### 4.2 前端

推荐：

```text
React + Vite + TypeScript
TanStack Table
Recharts 或 ECharts
React Router
```

或：

```text
Vue + Vite + TypeScript
Element Plus
ECharts
Vue Router
```

如果你更重视 Dashboard 和工程生态，建议 React。若更重视快速页面搭建，Vue 也合适。

### 4.3 后台任务

MVP 阶段：

```text
SQLite task 表
Python Worker
subprocess 或 asyncio
```

扩展阶段：

```text
Celery + Redis
或 RQ + Redis
```

建议先做轻量 Worker，等批量任务和重试需求明确后再引入 Celery。

## 5. 数据存储方案

### 5.1 SQLite

SQLite 存储结构化数据：

1. Paper。
2. Candidate。
3. Search Batch。
4. Project。
5. Task。
6. Note 状态。
7. File Asset。
8. Logs 索引。

### 5.2 文件系统

文件系统存储大文件和可读文件：

```text
workspace/
  inbox/
  curated/
  papers/
  archives/
  exports/
  logs/
```

Paper 标准目录：

```text
papers/
  domain/
    area/
      topic/
        slug/
          paper.pdf
          note.md
          refined.md
          metadata.yaml
          images/
          state.json
```

## 6. 前后端分工

| 功能 | 前端 | 后端 |
|---|---|---|
| Dashboard | 展示图表、列表、筛选 | 提供聚合 API |
| 搜索批次 | 展示批次和候选项 | 创建 batch、保存 candidate |
| Gate 1 | keep、reject、reset 操作 | 状态写入和 Curated 创建 |
| PDF 上传 | 拖拽、选择文件 | 保存文件、校验路径 |
| 解析任务 | 显示队列状态 | 创建任务、调用 Worker |
| Gate 2 | 展示分类建议和决策按钮 | 写入决策、迁移文件 |
| Library | 展示正式库和筛选 | 查询数据库和文件状态 |
| Obsidian 导出 | 触发导出 | 生成 Markdown 和目录 |

## 7. 文件安全策略

1. 所有路径必须在 workspace 内。
2. 文件移动前检查目标路径。
3. 目标存在时停止并进入 needs-review。
4. 删除操作默认进入应用级 archive，少用真实删除。
5. 所有迁移操作写入日志。
6. 用户手写 note 不允许被自动覆盖。
7. 自动生成内容需带 generated 标记。

## 8. 桌面封装策略

第一版不直接做 Electron。后续封装时采用：

```text
Electron / Tauri
  启动 FastAPI 本地后端
  加载前端静态资源
  管理窗口、托盘、系统通知
```

业务逻辑仍放在后端，避免桌面壳承担复杂流程。
