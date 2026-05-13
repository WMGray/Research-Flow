---
title: Research-Flow API 与实施
status: 草稿
updated: 2026-05-14
---

# Research-Flow API 与实施

## 1. API 约定

1. Base URL: `http://127.0.0.1:8000/api`
2. Response: JSON
3. MVP 阶段可先不做 Auth
4. 当前实现先落在本地数据库 + JSON，后续再迁移到正式数据库表结构

## 2. 核心接口

1. `GET /dashboard/home`
2. `GET /dashboard/papers-overview`
3. `GET /dashboard/discover`
4. `GET /dashboard/acquire`
5. `GET /dashboard/library`
6. `POST /search-batches`
7. `PATCH /candidates/{candidate_id}/decision`
8. `POST /search-batches/{batch_id}/apply-gate1`
9. `POST /papers/{paper_id}/parse`
10. `POST /papers/{paper_id}/classify`
11. `POST /papers/{paper_id}/gate2`
12. `POST /papers/{paper_id}/generate-note`
13. `POST /exports/obsidian`
14. `GET /tasks/{task_id}`

## 3. 统一响应

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

## 4. 验收标准

1. Search Batch 能创建和回看。
2. Gate 1 能把 keep 条目转入 Curated。
3. PDF 缺失会进入 needs-pdf。
4. 解析失败会进入 failed。
5. Gate 2 可 accept / modify / reject。
6. 导出不会覆盖用户手写 note。

## 5. 实施顺序

1. 先做本地数据库 + JSON 的读写层。
2. 再做数据模型和 Task。
3. 再做 Dashboard 聚合接口。
4. 再做 Discover 和 Acquire。
5. 再做 Library 和导出。
6. 最后把 JSON 结构逐步迁移到正式数据库。
