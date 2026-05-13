# PaperFlow Codex 实施任务

## 1. 使用原则

每次只交给 Codex 一个明确任务。避免让 Codex 同时修改架构、前端、后端、样式和数据模型。

任务格式建议：

```text
目标
范围
输入文件
输出文件
禁止事项
验收标准
```

## 2. Task 01 初始化项目

### 目标

创建本地 Web 项目骨架。

### 范围

```text
backend/
frontend/
docs/
workspace/
```

### 技术

```text
FastAPI
SQLite
React + Vite + TypeScript
```

### 验收

1. 后端可以启动。
2. 前端可以启动。
3. 前端能调用 `/api/health`。
4. SQLite 初始化成功。

## 3. Task 02 数据模型

### 目标

实现 Paper、SearchBatch、Candidate、Task 基础模型。

### 验收

1. 数据库表创建成功。
2. 支持创建 Paper。
3. 支持查询 Paper。
4. 支持创建 SearchBatch。
5. 支持 Candidate decision 更新。

## 4. Task 03 Papers Overview API

### 目标

实现 Dashboard 聚合 API。

### API

```text
GET /api/dashboard/home
GET /api/dashboard/papers-overview
```

### 验收

1. 返回统计数量。
2. 返回当前最该处理列表。
3. 返回最近更新列表。
4. 缺字段时不报错。

## 5. Task 04 Discover 页面

### 目标

实现 Search Batch 和 Candidate Review UI。

### 功能

1. 显示 batch 列表。
2. 展开 batch 查看 candidate。
3. keep、reject、reset。
4. apply gate1。

### 验收

1. 决策状态更新。
2. keep 条目可以进入 Curated。
3. 页面刷新后状态保留。

## 6. Task 05 Acquire 页面

### 目标

实现 Curated 论文处理界面。

### 功能

1. 显示 Curated paper。
2. 显示 PDF 状态。
3. 创建 parse task。
4. 显示分类建议。
5. Gate 2 accept、reject、reset。

### 验收

1. 缺 PDF 显示 needs-pdf。
2. 解析任务进入队列。
3. Gate 2 accept 后进入 Library。
4. reject 后进入 Archives。

## 7. Task 06 Worker

### 目标

实现轻量后台任务 Worker。

### 功能

1. 扫描 queued task。
2. 执行 parse_pdf 占位任务。
3. 写入 task 日志。
4. 更新 Paper 状态。

### 验收

1. task 可从 queued 到 running。
2. task 可从 running 到 succeeded。
3. 失败任务写入 error。
4. 服务重启后任务状态可查。

## 8. Task 07 Library 页面

### 目标

实现正式论文库浏览页面。

### 功能

1. Recent Papers。
2. By Domain。
3. By Year。
4. Read 状态。
5. Note 状态。

### 验收

1. 可以按 domain 筛选。
2. 可以按 year 聚合。
3. 可以更新 read_status。
4. 可以进入 Paper Detail。

## 9. Task 08 Obsidian 导出

### 目标

实现单篇论文导出到 Obsidian 目录。

### 输出

```text
paper.pdf
note.md
refined.md
metadata.yaml
images/
state.json
```

### 验收

1. 文件结构正确。
2. 不覆盖用户手写 note。
3. metadata.yaml 字段完整。
4. 导出日志可查。

## 10. Task 09 HomePage UI

### 目标

实现首页 Dashboard。

### 布局

```text
Hero
文献统计
研究信息
DDL
近期待办
Dashboard 跳转
```

### 验收

1. Open Papers 指向 Papers Overview。
2. Open Queue 指向 Acquire。
3. Hero 右侧显示图片区域。
4. 研究信息包含数字和圆环图。
5. Dashboard 跳转保留完整导航。

## 11. Task 10 文档同步

### 目标

根据实际实现更新 docs。

### 验收

1. README 更新。
2. API 草案更新。
3. 数据模型文档更新。
4. Roadmap 标记完成项。
