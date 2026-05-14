# Research-Flow

Research-Flow 是一个面向科研人员的本地优先研究工作台。

本轮落地的是 Paper MVP：以前后端分离架构承接 `05_Research` 中已有的文献处理流程，把 `data/` 作为唯一文献库真源，并先完成 HomePage 与后端脚本闭环。

## 目录

- `backend/`：FastAPI 服务、`PaperLibrary` 领域逻辑、`paper_library` CLI 与测试
- `frontend/`：Vite + React 前端壳，当前已实现 HomePage 与占位路由
- `data/`：本地文献库真源，包含 `Discover / Acquire / Library / templates`
- `docs/`：需求、架构、API、数据目录与 Paper 流程文档

## 快速启动

后端：

```bash
python -m uvicorn backend.app.main:app --reload
```

前端：

```bash
cd frontend
cmd /c npm install
cmd /c npm run dev
```

## 验证

后端测试：

```bash
python -m pytest backend/tests
python -m compileall backend
```

前端构建：

```bash
cd frontend
cmd /c npm run build
cmd /c npm run lint
```
