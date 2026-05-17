# Backend

后端当前采用 `FastAPI + 本地文件系统`，围绕 `Paper` 主流程实现，不接入 `Celery / Redis / skills / LLM Provider / 数据库`。

## 目录结构

```text
backend/
├── app/
│   ├── api/
│   ├── schemas/
│   ├── dependencies.py
│   └── main.py
├── core/
│   ├── config.py
│   └── services/
│       └── papers/
├── scripts/
│   └── paper_library.py
└── tests/
```

## 数据真源

- `data/Discover/`: search batch 与 candidate review 结果
- `data/01_Papers/`: 正式论文库
- `data/02_ReadingNotes/`: 阅读笔记与附属写作材料
- `data/03_References/`: 参考资料
- `data/templates/`: note 模板

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
python -m backend.scripts.paper_library ingest --input data/Discover/imports/example
python -m backend.scripts.paper_library migrate --input data/Discover/imports/example --domain Computer-Vision --area Video-Understanding --topic Action-Anticipation
python -m backend.scripts.paper_library note-template --title "Example Paper"
python -m backend.scripts.paper_library parse-pdf --paper-id <paper_id>
```

## 当前主流程接口

- `GET /health`
- `GET /api/dashboard/home`
- `GET /api/dashboard/papers-overview`
- `GET /api/dashboard/discover`
- `GET /api/dashboard/papers`
- `GET /api/papers`
- `GET /api/papers/{paper_id}`
- `GET /api/papers/{paper_id}/content`
- `PATCH /api/papers/{paper_id}/metadata`
- `PATCH /api/papers/{paper_id}/classification`
- `POST /api/papers/library-folders`
- `POST /api/papers/ingest`
- `POST /api/papers/migrate`
- `POST /api/papers/generate-note`
- `POST /api/papers/{paper_id}/generate-note`
- `POST /api/papers/{paper_id}/parse-pdf`
- `GET /api/papers/{paper_id}/parser-runs`
- `POST /api/papers/{paper_id}/reject`

## Paper 契约

当前 `PaperRecord` 已包含以下主流程真源字段：

- `stage`
- `asset_status`
- `parser_status`
- `review_status`
- `note_status`
- `parser_artifacts`
- `capabilities`
