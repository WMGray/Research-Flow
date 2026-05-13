# PaperFlow 需求规格说明

## 1. 背景

科研工作中，论文资料通常分散在浏览器、PDF 文件夹、Obsidian、Zotero、聊天记录和临时脚本中。用户需要在多个工具之间切换，完成检索、筛选、下载、解析、阅读、归档、分类和课题关联。现有流程存在几个核心痛点：

1. 论文从发现到入库缺少统一状态。
2. PDF、note、metadata、解析结果之间容易脱节。
3. 候选论文筛选和正式论文库混在一起。
4. 分类需要人工判断，但缺少可恢复的审核机制。
5. LLM 生成笔记后缺少结构化沉淀和质量状态。
6. Dashboard 只展示零散数据，缺少流程视角。
7. Obsidian 适合知识沉淀，但复杂流程管理和批处理能力有限。

PaperFlow 的目标是建立一个本地科研工作台，让论文从候选到正式入库形成可追踪、可审核、可恢复的流程。

## 2. 产品目标

### 2.1 核心目标

PaperFlow 需要完成以下目标：

1. 管理论文全生命周期。
2. 支持论文检索结果的候选筛选。
3. 支持 trusted PDF 的本地导入、解析与入库。
4. 支持 LLM 辅助分类和笔记生成。
5. 支持人工审核门控，避免自动错误入库。
6. 支持 Dashboard 展示整体状态、异常、待办和最近更新。
7. 支持导出到 Obsidian Vault，保留 Markdown 友好结构。
8. 后续支持课题管理、论文与课题关联、研究路线沉淀。

### 2.2 非目标

第一版暂不做：

1. 完整替代 Zotero。
2. 自动绕过付费墙获取 PDF。
3. 强制要求 BibTeX 或 citation key。
4. 自动决定最终研究分类。
5. 复杂知识图谱推理。
6. 多用户权限系统。
7. 云同步和团队协作。
8. 完整桌面打包发布。

## 3. 目标用户

| 用户 | 场景 | 需求 |
|---|---|---|
| 研究生 | 日常读论文、整理课题 | 快速管理论文状态，减少手工维护 |
| 深度学习研究者 | 追踪会议论文和方向进展 | 批量筛选、分类、生成结构化笔记 |
| 工程型科研人员 | 管理 PDF、脚本、结果文件 | 文件与状态统一，任务可恢复 |
| Obsidian 用户 | 希望保留 Markdown 知识库 | 支持 Vault 导出和双向链接 |

## 4. 核心场景

### 4.1 论文发现

用户输入主题、关键词、会议、年份范围，系统检索候选论文，生成 Search Batch。用户在候选列表中执行 keep、reject、pending，Gate 1 通过后进入 Curated Queue。

### 4.2 PDF 获取与解析

用户为 Curated 论文补齐 PDF。系统检查文件完整性，调用解析流程生成 refined.md、images 和结构化 metadata。缺少 PDF 时进入 needs-pdf。

### 4.3 分类审核与入库

系统基于 taxonomy、metadata、摘要和 refined 内容生成分类建议。用户确认或修改后执行 Gate 2，论文进入正式库。拒绝项进入 Archives。

### 4.4 阅读笔记生成

正式入库论文可以调用 LLM 生成 note.md。用户阅读后标记 reviewed、read、project relevance 等字段。

### 4.5 Dashboard 总览

首页展示总体统计、近期待办、会议 DDL、研究信息和 Dashboard 跳转。Papers Dashboard 按 Discover、Acquire、Library 三阶段组织。

## 5. 功能需求

### 5.1 Paper 管理

| 编号 | 需求 | 优先级 |
|---|---|---|
| P1 | 创建 Paper 记录，保存 title、authors、year、venue、doi、url、abstract | P0 |
| P2 | 支持本地 PDF 绑定到 Paper | P0 |
| P3 | 支持 metadata.yaml 或等价数据库字段 | P0 |
| P4 | 支持 paper 状态流转 | P0 |
| P5 | 支持 paper 与本地文件夹路径关联 | P0 |
| P6 | 支持 note、refined、images、state 文件管理 | P0 |
| P7 | 支持批量导入 PDF | P1 |
| P8 | 支持重复论文检测 | P1 |

### 5.2 Discover

| 编号 | 需求 | 优先级 |
|---|---|---|
| D1 | 支持按 query 创建 Search Batch | P0 |
| D2 | 支持记录候选论文元数据 | P0 |
| D3 | 支持 keep、reject、pending、reset | P0 |
| D4 | 支持 Gate 1 apply，将 keep 条目写入 Curated | P0 |
| D5 | 支持来源证据和摘要展示 | P1 |
| D6 | 支持本地库去重提示 | P1 |

### 5.3 Acquire

| 编号 | 需求 | 优先级 |
|---|---|---|
| A1 | 检查 Curated 论文是否已有 paper.pdf | P0 |
| A2 | 缺少 PDF 时标记 needs-pdf | P0 |
| A3 | 调用 PDF 解析流程生成 refined.md 和 images | P0 |
| A4 | 生成分类建议 | P0 |
| A5 | 支持 Gate 2 accept、modify、reject、pending | P0 |
| A6 | Gate 2 通过后迁移到正式库 | P0 |
| A7 | 路径冲突时进入 needs-review | P0 |
| A8 | 记录错误和处理日志 | P0 |

### 5.4 Library

| 编号 | 需求 | 优先级 |
|---|---|---|
| L1 | 展示正式论文库 | P0 |
| L2 | 支持按 domain、area、topic、year、venue 聚合 | P0 |
| L3 | 展示 note 状态和 read 状态 | P0 |
| L4 | 支持未分类论文列表 | P0 |
| L5 | 支持生成或更新 note.md | P1 |
| L6 | 支持与课题关联 | P1 |

### 5.5 Project 管理

| 编号 | 需求 | 优先级 |
|---|---|---|
| R1 | 创建课题记录 | P1 |
| R2 | 绑定相关论文 | P1 |
| R3 | 记录研究问题、方法、实验计划、投稿目标 | P1 |
| R4 | 显示课题路线图 | P2 |
| R5 | 从论文笔记中提取 idea | P2 |

### 5.6 Obsidian 导出

| 编号 | 需求 | 优先级 |
|---|---|---|
| O1 | 导出 paper 目录结构 | P0 |
| O2 | 导出 note.md、metadata.yaml、refined.md | P0 |
| O3 | 支持 Dashboard Markdown 页面 | P1 |
| O4 | 支持 Wikilink 路径 | P1 |
| O5 | 支持增量导出 | P1 |

## 6. 约束

1. 第一版本地运行。
2. 数据库存 SQLite。
3. 文件存储在用户指定 workspace。
4. 后端使用 Python。
5. 前端使用 Web 技术。
6. 后台任务需可恢复。
7. 任何文件迁移不得静默覆盖。
8. PDF 缺失时不得自动假设已完成。
9. 分类建议必须保留人工确认入口。
10. 日志需使用中文，便于事后排查。

## 7. 成功指标

1. 单篇论文可以完成从 Curated 到正式库的完整流程。
2. 批量候选可以通过 Gate 1 进入 Curated。
3. 缺 PDF、解析失败、分类待审核均可在 Dashboard 中看到。
4. 用户可以在 3 次点击内进入当前最该处理的论文。
5. Obsidian 导出的目录可以直接浏览。
6. 已入库论文有稳定路径、metadata、note、refined 和 PDF。
