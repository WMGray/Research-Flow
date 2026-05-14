---
title: Research-Flow API 与实施
status: draft
updated: 2026-05-14
---

# Research-Flow API 与实施

## API 基线

- Base URL: `http://127.0.0.1:8000`
- Response shape:

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

## 已实现接口

### Dashboard

1. `GET /health`
2. `GET /api/dashboard/home`
3. `GET /api/dashboard/papers-overview`
4. `GET /api/dashboard/discover`
5. `GET /api/dashboard/acquire`
6. `GET /api/dashboard/library`

### Papers

1. `GET /api/papers`
2. `GET /api/papers/{paper_id}`
3. `POST /api/papers/ingest`
4. `POST /api/papers/migrate`
5. `POST /api/papers/generate-note`

## CLI

```bash
python -m backend.scripts.paper_library scan
python -m backend.scripts.paper_library ingest --input data/Acquire/curated/<slug>
python -m backend.scripts.paper_library migrate --input data/Acquire/curated/<slug> --domain Computer-Vision --area Video-Understanding --topic Action-Anticipation
python -m backend.scripts.paper_library note-template --title "Example Paper"
```

## 验收标准

1. 后端可以启动并返回 `health`。
2. HomePage 可以读取真实 dashboard 数据。
3. `data/Acquire` 中的样本可以被迁移到 `data/Library`。
4. 目标目录冲突时不会静默覆盖。
5. `needs-pdf / needs-review / failed / processed` 能进入首页统计。

