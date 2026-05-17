# Frontend

前端采用 React + TypeScript + Vite，当前主工作流已经收敛为 `Home -> Discover -> Papers`。

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

- `/`：HomePage，展示总览统计、研究信息、待处理队列与最近 batch
- `/discover`：候选论文发现与筛选
- `/papers`、`/papers/:paperId`：论文库工作台与详情面板
- `/uncategorized`：未分类论文视图
- `/archive`：归档只读视图
- `/settings`：配置页
