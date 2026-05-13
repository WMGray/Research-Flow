# PaperFlow 数据模型与状态机

## 1. 实体总览

```text
Paper
Candidate
SearchBatch
Project
Topic
Task
Note
FileAsset
ReviewDecision
ExportJob
```

## 2. Paper

Paper 是正式或准正式论文对象，覆盖从 Curated 到 Library 的全过程。

### 2.1 字段

```yaml
id: ""
title: ""
authors: []
year: null
venue: ""
doi: ""
arxiv_id: ""
openreview_id: ""
paper_url: ""
pdf_url: ""
abstract: ""
source_type: ""
stage: ""
status: ""
domain: ""
area: ""
topic: ""
tags: []
slug: ""
workspace_path: ""
pdf_path: ""
note_path: ""
refined_path: ""
images_path: ""
metadata_path: ""
state_path: ""
note_status: ""
read_status: ""
classification_confidence: ""
classification_reason: ""
summary: ""
contributions: []
limitations: []
project_relevance: ""
created_at: ""
updated_at: ""
```

### 2.2 stage

| stage | 含义 |
|---|---|
| discovered | 检索发现 |
| curated | 通过 Gate 1，进入 Curated |
| acquired | PDF 和解析结果已具备 |
| classified | 分类已确认 |
| library | 进入正式库 |
| understood | note 已生成并经过阅读处理 |
| archived | 已归档 |

### 2.3 status

| status | 含义 |
|---|---|
| pending | 等待处理 |
| needs-pdf | 缺少 paper.pdf |
| needs-review | 需要人工审核 |
| queued | 任务排队中 |
| running | 任务执行中 |
| processed | 已处理 |
| failed | 处理失败 |
| archived | 已归档 |

## 3. Candidate

Candidate 属于 Search Batch，代表待筛选论文。

```yaml
id: ""
batch_id: ""
title: ""
authors: []
year: null
venue: ""
doi: ""
arxiv_id: ""
url: ""
pdf_url: ""
abstract: ""
source_type: ""
decision: "pending"
decision_reason: ""
duplicate_of: ""
has_pdf: false
created_at: ""
updated_at: ""
```

decision 取值：

| decision | 含义 |
|---|---|
| pending | 未决策 |
| keep | 保留 |
| reject | 拒绝 |
| reset | 重置为未决策 |

## 4. SearchBatch

```yaml
id: ""
query: ""
sources: []
venue_filter: []
year_min: null
year_max: null
candidate_count: 0
keep_count: 0
reject_count: 0
pending_count: 0
status: ""
created_at: ""
updated_at: ""
```

## 5. Project

```yaml
id: ""
name: ""
description: ""
research_question: ""
status: ""
target_venue: ""
deadline: ""
paper_ids: []
tags: []
created_at: ""
updated_at: ""
```

## 6. Task

后台任务统一使用 Task 实体记录。

```yaml
id: ""
task_type: ""
target_type: ""
target_id: ""
status: ""
progress: 0
input: {}
output: {}
error: ""
logs: []
created_at: ""
started_at: ""
finished_at: ""
```

task_type 示例：

| task_type | 含义 |
|---|---|
| search | 外部检索 |
| parse_pdf | PDF 解析 |
| classify | 分类建议 |
| generate_note | 生成阅读笔记 |
| export_obsidian | 导出到 Obsidian |
| migrate | 文件迁移 |

status 示例：

| status | 含义 |
|---|---|
| queued | 排队 |
| running | 执行中 |
| succeeded | 成功 |
| failed | 失败 |
| canceled | 取消 |
| retrying | 重试中 |

## 7. ReviewDecision

```yaml
id: ""
target_type: ""
target_id: ""
gate: ""
suggested: {}
decision: ""
decision_payload: {}
reason: ""
operator: ""
created_at: ""
updated_at: ""
```

gate 示例：

| gate | 含义 |
|---|---|
| gate1 | 候选论文筛选 |
| gate2 | 分类与入库审核 |

## 8. 状态机

### 8.1 论文主状态流

```text
discovered
  ↓ Gate 1 keep
curated
  ↓ PDF ready
acquired
  ↓ parse ok
needs-review
  ↓ Gate 2 accept
library
  ↓ note generated
understood
```

异常分支：

```text
curated
  ↓ missing pdf
needs-pdf

acquired
  ↓ parse failed
failed

needs-review
  ↓ Gate 2 reject
archived
```

### 8.2 Gate 1

输入：

```text
SearchBatch Candidate
```

输出：

```text
keep -> Curated Paper
reject -> 保留在 batch
pending -> 保持未处理
```

### 8.3 Gate 2

输入：

```text
Curated Paper
classification suggestion
```

输出：

```text
accept -> 正式库
modify -> 按修改后的分类进入正式库
reject -> Archives
pending -> 继续待审核
```

## 9. Metadata 文件

导出到 Obsidian 时，每篇论文生成 metadata.yaml。

```yaml
title: ""
authors: []
year: null
venue: ""
doi: ""
arxiv_id: ""
paper_url: ""
pdf_url: ""
domain: ""
area: ""
topic: ""
stage: ""
status: ""
note_status: ""
read_status: ""
tags:
  - paper
created_at: ""
updated_at: ""
```

## 10. Note 状态

| note_status | 含义 |
|---|---|
| none | 无 note |
| template | 只有模板 |
| generated | LLM 已生成 |
| reviewed | 用户已审核 |
| revised | 用户已修改 |

| read_status | 含义 |
|---|---|
| unread | 未读 |
| reading | 阅读中 |
| read | 已读 |
| skipped | 跳过 |
