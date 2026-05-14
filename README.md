# Research-Flow

Research-Flow 是一个面向研究流程的本地优先工作台。当前阶段聚焦 Paper 全流程：以根目录 `data/` 为唯一真源，先完成 Discover、Acquire、Library、Paper Detail、Config 与程序式 PDF parser 的可维护闭环。

## 目录

- `backend/`：FastAPI 后端，当前已按 `app / core / scripts / tests` 分层
- `frontend/`：Vite + React 前端，当前实现 HomePage 与 Paper 全流程页面壳
- `data/`：唯一数据真源，包含 `Discover / Acquire / Library / templates`
- `docs/`：按 `master` 风格整理的分层文档中心

## 文档入口

- 总索引：`docs/README.md`
- 需求与路线图：`docs/00_overview/`
- 前端说明：`docs/01_frontend/`
- 后端说明：`docs/02_backend/`
- API 规范：`docs/03_api/`
- 参考截图：`docs/04_reference/`

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

后端：

```bash
python -m pytest backend/tests
python -m compileall backend
python -m backend.scripts.paper_library scan
```

前端：

```bash
cd frontend
cmd /c npm run build
cmd /c npm run lint
```
