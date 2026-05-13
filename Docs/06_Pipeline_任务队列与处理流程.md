# PaperFlow 任务队列与处理流程

## 1. Pipeline 总览

```text
Discover
  检索与候选收集

Gate 1
  初筛 keep / reject / pending

Curated
  候选进入处理队列

Acquire
  PDF 检查、解析、分类建议

Gate 2
  accept / modify / reject

Library
  正式库、阅读笔记、课题关联
```

## 2. Discover Pipeline

### 输入

```text
query
source list
venue filter
year range
```

### 输出

```text
SearchBatch
Candidate[]
```

### 步骤

1. 创建 Search Batch。
2. 检索候选论文。
3. 补全基础元数据。
4. 本地去重。
5. 写入 Candidate。
6. 用户进行 keep、reject、pending。
7. Gate 1 apply 把 keep 项转为 Paper，并进入 Curated。

## 3. Acquire Pipeline

### 输入

```text
Curated Paper
paper.pdf
metadata
```

### 输出

```text
refined.md
images/
classification suggestion
classification.review
```

### 步骤

1. 检查 paper.pdf。
2. 缺失时进入 needs-pdf。
3. 创建 parse_pdf task。
4. Worker 执行 PDF 解析。
5. 写入 refined.md 和 images。
6. 调用 LLM 分类建议。
7. 生成 Gate 2 review。
8. 用户 accept、modify、reject。
9. 按决策迁移到正式库或 Archives。

## 4. Understand Pipeline

### 输入

```text
Library Paper
refined.md
metadata.yaml
```

### 输出

```text
note.md
summary
contributions
limitations
project_relevance
```

### 步骤

1. 读取 refined.md。
2. 读取 metadata。
3. 调用 LLM 生成 note。
4. 写入 note.md。
5. 更新 note_status。
6. 用户阅读后更新 read_status 和 reviewed 状态。

## 5. Export Pipeline

### 输入

```text
PaperFlow database
file assets
export config
```

### 输出

```text
Obsidian Vault compatible directory
```

### 步骤

1. 计算导出路径。
2. 生成或更新 metadata.yaml。
3. 生成或更新 note.md。
4. 复制 PDF、refined、images。
5. 生成 Dashboard Markdown。
6. 写入导出日志。

## 6. Task Queue 设计

### 6.1 MVP 方案

使用 SQLite task 表。

```text
task inserted
worker polls task
worker locks task
worker runs task
worker writes status
frontend polls API
```

### 6.2 后续方案

使用 Celery 或 RQ。

```text
FastAPI
Redis
Celery Worker
SQLite
File Store
```

## 7. Task 类型

| 类型 | 说明 |
|---|---|
| search | 检索论文 |
| ingest_candidate | Candidate 转 Curated |
| parse_pdf | PDF 解析 |
| classify | 分类建议 |
| apply_gate2 | Gate 2 迁移 |
| generate_note | 生成笔记 |
| export_obsidian | 导出 Obsidian |
| scan_workspace | 扫描文件状态 |

## 8. 错误处理

| 错误 | 处理 |
|---|---|
| PDF 缺失 | status = needs-pdf |
| title 缺失 | status = needs-review |
| 目标目录存在 | status = needs-review |
| PDF 解析失败 | status = failed |
| LLM 调用失败 | task failed，可重试 |
| 文件移动失败 | 停止迁移，写入日志 |

## 9. 日志

每次实际处理写入日志。

日志字段：

```text
time
task_type
target_id
input_path
output_path
paper_title
doi
stage
status
error
next_action
```

## 10. 并发策略

MVP：

```text
parse_pdf 并发 1 到 3
classify 并发 1
generate_note 并发 1 到 2
export 并发 1
```

后续按模型限制、API rate limit 和本地资源调整。
