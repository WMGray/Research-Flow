# PaperFlow 信息架构与页面设计

## 1. 页面总览

```text
Home
Papers
  Overview
  Discover
  Acquire
  Library
Projects
  Overview
  Project Detail
Runtime
Logs
Settings
```

## 2. Home

Home 是总入口，展示整体状态和跳转。

### 2.1 布局

```text
Hero
  左侧：标题、说明、Open Papers、Open Queue
  右侧：研究主题图片

第二行
  文献总数统计
  研究信息
  重要会议 DDL

第三行
  近期待办
  Dashboard 跳转
```

### 2.2 交互

| 按钮 | 目标 |
|---|---|
| Open Papers | Papers Overview |
| Open Queue | Acquire |
| Papers Overview | Papers Overview |
| Discover | Discover |
| Acquire | Acquire |
| Library | Library |
| Runtime | Runtime |
| Logs | Logs |

## 3. Papers Overview

### 3.1 页面目标

帮助用户快速判断论文流程卡在哪里。

### 3.2 内容

1. 三阶段流程概览：Discover、Acquire、Library。
2. 核心统计卡片。
3. 当前最该处理。
4. 最近入库和更新。
5. 阶段页面入口。

### 3.3 指标

```text
Discover Candidates
Curated Queue
Final Papers
Notes Pending
Search Batches
Gate 1 Keep
Acquire Queue
Final Papers
```

## 4. Discover Dashboard

### 4.1 页面目标

处理 Search Batch 和 Gate 1。

### 4.2 内容

1. 批次统计。
2. Search Batch 列表。
3. Candidate 表格。
4. keep、reject、reset 操作。
5. Ingest Approved 按钮。

### 4.3 Candidate 行信息

```text
title
year
venue
source
abstract summary
decision
pdf status
actions
```

## 5. Acquire Dashboard

### 5.1 页面目标

处理 Curated 论文的 PDF、解析、分类和 Gate 2。

### 5.2 内容

1. Curated 队列。
2. PDF 状态。
3. Parse 状态。
4. LLM 分类状态。
5. Review 状态。
6. Confirm 状态。
7. 分类建议。
8. 操作按钮。

### 5.3 Paper 处理卡片

左侧：

```text
path
title
Parse status
LLM status
Review status
Confirm status
refined / note / state / pdf
```

右侧：

```text
Domain
Area
Topic
classification confidence
Retry Parse
Reset Review
Accept
Reject
Reset Decision
```

## 6. Library Dashboard

### 6.1 页面目标

浏览正式论文库，管理阅读和笔记状态。

### 6.2 内容

1. Papers 总数。
2. Template 数量。
3. Generated 数量。
4. Reviewed 数量。
5. Read 数量。
6. Unclassified 数量。
7. By Domain。
8. By Year。
9. Recent Papers。
10. Filter：All、Unread、Read。

### 6.3 Recent Papers 行信息

```text
category path
title
venue
year
note status
read status
file links
actions
```

## 7. Paper Detail

### 7.1 页面目标

展示单篇论文的完整信息和可执行动作。

### 7.2 内容

1. 标题、作者、年份、会议。
2. PDF 预览。
3. Metadata。
4. Abstract。
5. refined.md 预览。
6. note.md 预览。
7. 分类建议和历史。
8. 任务日志。
9. 关联 Project。
10. 操作区。

### 7.3 操作

```text
Bind PDF
Parse PDF
Generate Note
Classify
Accept to Library
Archive
Export to Obsidian
```

## 8. Runtime

### 8.1 页面目标

管理后台任务和错误。

### 8.2 内容

1. Task Queue。
2. Running Tasks。
3. Failed Tasks。
4. Recent Logs。
5. Retry。
6. Cancel。

## 9. Settings

### 9.1 内容

1. Workspace 路径。
2. Obsidian Vault 路径。
3. LLM 配置。
4. MinerU 配置。
5. Semantic Scholar / OpenAlex 配置。
6. 导出配置。
7. 主题配置。

## 10. 视觉原则

1. Dashboard 页面采用卡片式布局。
2. 首页减少表格，阶段页面可以使用表格。
3. 状态标签数量要克制。
4. 主行动按钮只保留一到两个。
5. 页面导航和执行按钮分离。
6. 大量数据使用筛选表格，少量核心数据使用指标卡。
