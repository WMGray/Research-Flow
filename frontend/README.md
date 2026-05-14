# Frontend

前端采用 React + TypeScript + Vite，当前只落地 HomePage、基础布局与占位路由。

## 运行

```bash
cd frontend
cmd /c npm install
cmd /c npm run dev
```

## 构建与检查

```bash
cd frontend
cmd /c npm run build
cmd /c npm run lint
```

## 环境变量

- `VITE_API_BASE_URL`：后端 API 地址，默认 `http://127.0.0.1:8000`

## 当前页面

- `/`：HomePage，展示总览统计、研究信息、待处理队列、Dashboard 跳转与 Recent Batches
- `/overview`、`/discover`、`/acquire`、`/library`、`/runtime`、`/logs`：占位页
