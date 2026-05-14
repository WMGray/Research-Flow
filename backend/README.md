# Backend

后端采用 FastAPI + 本地文件系统，不接 Celery、Redis 或 skills。

## 数据目录

- `data/Discover/`：搜索批次
- `data/Acquire/`：待入库论文
- `data/Library/`：正式文献库
- `data/templates/`：笔记模板

## 运行

```bash
python -m uvicorn backend.app.main:app --reload
```

## 测试

```bash
python -m pytest backend/tests
python -m compileall backend
```

## 脚本

```bash
python -m backend.scripts.paper_library scan
python -m backend.scripts.paper_library ingest --input data/Acquire/curated/example
python -m backend.scripts.paper_library migrate --input data/Acquire/curated/example --domain 计算机视觉 --area 视频理解 --topic 动作预测
python -m backend.scripts.paper_library note-template --title "Example Paper"
```

## 已实现接口

- `GET /health`
- `GET /api/dashboard/home`
- `GET /api/dashboard/papers-overview`
- `GET /api/dashboard/discover`
- `GET /api/dashboard/acquire`
- `GET /api/dashboard/library`
- `GET /api/papers`
- `GET /api/papers/{paper_id}`
- `POST /api/papers/ingest`
- `POST /api/papers/migrate`
- `POST /api/papers/generate-note`
