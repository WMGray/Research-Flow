# PaperFlow 验收与测试

## 1. MVP 验收目标

MVP 需要证明系统能够完成论文从候选到正式库的闭环。

核心闭环：

```text
Search Batch
Candidate keep
Curated
PDF bound
Parse task
Classification review
Gate 2 accept
Library
Note generated
Dashboard updated
```

## 2. 功能验收

### 2.1 Discover

| 用例 | 输入 | 期望 |
|---|---|---|
| 创建 Search Batch | query | 生成 batch |
| 更新 Candidate 决策 | keep | decision 变为 keep |
| 应用 Gate 1 | batch | keep 项进入 Curated |
| reject 候选 | reject | 不进入 Curated |
| pending 候选 | pending | 保持在 batch |

### 2.2 Acquire

| 用例 | 输入 | 期望 |
|---|---|---|
| 缺少 PDF | Curated paper | status = needs-pdf |
| 绑定 PDF | paper.pdf | pdf_path 写入 |
| 创建解析任务 | paper_id | task = queued |
| 解析成功 | PDF | refined.md 生成 |
| 解析失败 | 错误 PDF | status = failed |
| 分类建议 | refined.md | 生成 suggested domain / area / topic |
| Gate 2 accept | 分类确认 | 进入正式库 |
| Gate 2 reject | 拒绝 | 进入 Archives |
| 目标路径冲突 | 已有目录 | status = needs-review |

### 2.3 Library

| 用例 | 输入 | 期望 |
|---|---|---|
| 查看正式库 | library page | 显示 processed papers |
| 按领域聚合 | domain | 显示 count |
| 按年份聚合 | year | 显示 count |
| 生成 note | paper_id | note.md 生成 |
| 标记已读 | read | read_status 更新 |

### 2.4 Obsidian 导出

| 用例 | 输入 | 期望 |
|---|---|---|
| 导出单篇 | paper | 生成标准目录 |
| 导出 Dashboard | all | 生成 Markdown dashboard |
| 增量导出 | 修改一篇 | 只更新相关文件 |
| 用户手写 note | 已存在 note | 不覆盖 |

## 3. 非功能验收

| 项目 | 标准 |
|---|---|
| 本地启动 | 30 秒内可打开 |
| 页面响应 | 常规列表 1 秒内返回 |
| 文件安全 | 不允许 workspace 外路径写入 |
| 迁移安全 | 目标存在时停止 |
| 日志 | 失败任务必须可追踪 |
| 可恢复 | 服务重启后任务状态仍可查看 |
| 可导出 | 数据可以导出为 Markdown 和文件目录 |

## 4. 测试数据

准备 10 篇测试论文：

1. 3 篇有完整 PDF。
2. 2 篇缺 PDF。
3. 2 篇 metadata 不完整。
4. 1 篇 title 缺失。
5. 1 篇路径冲突。
6. 1 篇解析失败模拟。

## 5. 回归测试清单

每次发布前检查：

1. 首页统计正常。
2. Papers Overview 正常。
3. Discover 列表正常。
4. Gate 1 正常。
5. Acquire 队列正常。
6. Parse 任务正常。
7. Gate 2 正常。
8. Library 聚合正常。
9. Note 生成正常。
10. Obsidian 导出正常。
11. 文件不会被静默覆盖。
12. 日志可以定位错误。

## 6. MVP 完成定义

MVP 完成需要满足：

1. 用户可以导入或创建候选论文。
2. 用户可以筛选候选论文。
3. 用户可以绑定 PDF。
4. 系统可以处理 PDF 并生成占位或真实解析结果。
5. 用户可以审核分类。
6. 系统可以把论文迁移到正式库。
7. 用户可以看到 Dashboard 更新。
8. 用户可以导出到 Obsidian。
