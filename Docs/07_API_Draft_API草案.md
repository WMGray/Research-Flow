# PaperFlow API 草案

## 1. 约定

```text
Base URL: http://127.0.0.1:8000/api
Response: JSON
Auth: MVP 阶段可不启用
```

统一响应：

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

错误响应：

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "needs_pdf",
    "message": "缺少 paper.pdf",
    "detail": {}
  }
}
```

## 2. Papers

### 创建 Paper

```http
POST /papers
```

请求：

```json
{
  "title": "Paper title",
  "year": 2025,
  "venue": "CVPR",
  "doi": "",
  "tags": ["paper"]
}
```

### 获取 Paper 列表

```http
GET /papers?stage=library&status=processed&domain=计算机视觉
```

### 获取单篇 Paper

```http
GET /papers/{paper_id}
```

### 更新 Paper

```http
PATCH /papers/{paper_id}
```

### 绑定 PDF

```http
POST /papers/{paper_id}/pdf
```

### 归档 Paper

```http
POST /papers/{paper_id}/archive
```

## 3. Search Batch

### 创建检索批次

```http
POST /search-batches
```

请求：

```json
{
  "query": "egocentric action anticipation",
  "sources": ["arxiv", "semantic_scholar"],
  "venue_filter": ["CVPR", "ICCV", "NeurIPS"],
  "year_min": 2020,
  "year_max": 2026
}
```

### 获取批次列表

```http
GET /search-batches
```

### 获取批次详情

```http
GET /search-batches/{batch_id}
```

### 更新 Candidate 决策

```http
PATCH /candidates/{candidate_id}/decision
```

请求：

```json
{
  "decision": "keep",
  "reason": "与动作预期方向相关"
}
```

### 应用 Gate 1

```http
POST /search-batches/{batch_id}/apply-gate1
```

## 4. Acquire

### 获取 Curated 列表

```http
GET /acquire/curated
```

### 创建解析任务

```http
POST /papers/{paper_id}/parse
```

### 创建分类建议任务

```http
POST /papers/{paper_id}/classify
```

### 获取 Gate 2 审核信息

```http
GET /papers/{paper_id}/gate2
```

### 提交 Gate 2 决策

```http
POST /papers/{paper_id}/gate2
```

请求：

```json
{
  "decision": "accept",
  "domain": "计算机视觉",
  "area": "视频理解",
  "topic": "动作预测",
  "reason": "论文关注 action anticipation"
}
```

## 5. Library

### 获取正式库

```http
GET /library/papers
```

### 获取聚合统计

```http
GET /library/stats
```

### 生成 Note

```http
POST /papers/{paper_id}/generate-note
```

### 更新阅读状态

```http
PATCH /papers/{paper_id}/read-status
```

请求：

```json
{
  "read_status": "read"
}
```

## 6. Dashboard

### 首页统计

```http
GET /dashboard/home
```

响应：

```json
{
  "papers": {
    "search": 5,
    "curated": 3,
    "final": 13,
    "reviewed_notes": 0,
    "needs_review": 3,
    "failed": 0,
    "total": 24
  },
  "recent_tasks": [],
  "ddl": []
}
```

### Papers Overview

```http
GET /dashboard/papers-overview
```

### Discover Dashboard

```http
GET /dashboard/discover
```

### Acquire Dashboard

```http
GET /dashboard/acquire
```

### Library Dashboard

```http
GET /dashboard/library
```

## 7. Tasks

### 获取任务列表

```http
GET /tasks?status=running
```

### 获取任务详情

```http
GET /tasks/{task_id}
```

### 重试任务

```http
POST /tasks/{task_id}/retry
```

### 取消任务

```http
POST /tasks/{task_id}/cancel
```

## 8. Export

### 导出到 Obsidian

```http
POST /exports/obsidian
```

请求：

```json
{
  "target_path": "/path/to/vault",
  "mode": "incremental"
}
```

### 获取导出任务

```http
GET /exports/{export_id}
```
