# Backend

后端当前采用 `FastAPI + 本地文件系统`，只落地 Paper 全流程，不接 Celery、Redis、skills、LLM Provider 或数据库。

## 目录结构

```text
backend/
├─ app/
│  ├─ api/          # FastAPI routers
│  ├─ schemas/      # Pydantic request/response schemas
│  ├─ dependencies.py
│  └─ main.py       # application entry
├─ core/
│  ├─ config.py     # shared settings
│  └─ services/
│     └─ papers/    # repository, service, models, utils
├─ scripts/
│  └─ paper_library.py
└─ tests/
```

## 数据真源

- `data/Discover/`：search batch 与 review 结果
- `data/Acquire/`：待入库论文
- `data/Library/`：正式本地文献库
- `data/templates/`：note 模板

## 运行

```bash
python -m uvicorn backend.app.main:app --reload
```

## 测试

```bash
python -m pytest backend/tests
python -m compileall backend
```

## CLI

```bash
python -m backend.scripts.paper_library scan
python -m backend.scripts.paper_library ingest --input data/Acquire/curated/example
python -m backend.scripts.paper_library migrate --input data/Acquire/curated/example --domain Computer-Vision --area Video-Understanding --topic Action-Anticipation
python -m backend.scripts.paper_library note-template --title "Example Paper"
python -m backend.scripts.paper_library parse-pdf --paper-id <paper_id>
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

## 下一步接口

- `GET /api/config`
- `POST /api/papers/{paper_id}/parse-pdf`
- `GET /api/papers/{paper_id}/parser-runs`
