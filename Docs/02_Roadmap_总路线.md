# PaperFlow 总路线

## 1. 总体策略

第一阶段以本地 Web 应用为核心，优先跑通论文闭环。桌面软件封装放在功能稳定之后。整体路线分为六个阶段：

```text
M0 需求收敛
M1 Web MVP
M2 Pipeline 完整化
M3 Obsidian 导出增强
M4 Project 与 Knowledge 扩展
M5 桌面封装
```

## 2. M0 需求收敛

### 目标

形成稳定的需求、数据模型、页面结构和工程边界。

### 交付物

1. PRD。
2. 总路线。
3. 系统设计方案。
4. 数据模型。
5. UI 信息架构。
6. API 草案。
7. 验收标准。

### 完成标准

1. Paper 生命周期定义完成。
2. Gate 1 和 Gate 2 语义明确。
3. 核心实体和状态字段明确。
4. MVP 范围明确。

## 3. M1 Web MVP

### 目标

实现可运行的本地 Web 版本，完成论文基础管理和 Dashboard 展示。

### 功能范围

1. Paper CRUD。
2. Search Batch 管理。
3. Candidate keep、reject、pending。
4. Curated Queue。
5. PDF 文件绑定。
6. 基础 metadata 管理。
7. Papers Overview。
8. Discover Dashboard。
9. Acquire Dashboard。
10. Library Dashboard。

### 技术范围

```text
FastAPI
SQLite
SQLAlchemy 或 SQLModel
React 或 Vue
本地文件存储
```

### 完成标准

1. 可以创建 Search Batch。
2. 可以把 keep 条目加入 Curated。
3. 可以为 Curated 论文绑定 PDF。
4. 可以进入 needs-pdf、needs-review、processed、failed。
5. 可以在 Dashboard 中看到状态统计。

## 4. M2 Pipeline 完整化

### 目标

让论文从 PDF 到正式库形成可恢复的流程。

### 功能范围

1. PDF 解析任务。
2. refined.md 和 images 输出。
3. LLM 分类建议。
4. classification.review 数据结构。
5. Gate 2 accept、modify、reject。
6. 路径迁移。
7. 任务失败重试。
8. 中文日志。

### 后台任务策略

M2 初期可使用 SQLite task 表和 Python Worker。任务量增加后再引入 Celery 或 RQ。

### 完成标准

1. PDF 解析任务可排队。
2. 解析失败可查看原因。
3. Gate 2 通过后论文进入正式库。
4. 拒绝论文进入 Archives。
5. 目标路径冲突不会覆盖原文件。

## 5. M3 Obsidian 导出增强

### 目标

让 PaperFlow 管理的数据可以稳定输出到 Obsidian Vault。

### 功能范围

1. 生成 Papers 目录。
2. 生成 HomePage 页面。
3. 生成 Papers Dashboard 四页面。
4. 生成 metadata.yaml。
5. 生成 note.md。
6. 生成 Dataview 兼容 frontmatter。
7. 增量同步。

### 完成标准

1. 导出的 vault 可以在 Obsidian 中正常浏览。
2. Dataview 可以自动展示论文状态。
3. 用户可在 Obsidian 中继续人工阅读和编辑 note。
4. 再次导出不会覆盖用户手写内容。

## 6. M4 Project 与 Knowledge 扩展

### 目标

从论文管理扩展到课题管理和研究知识沉淀。

### 功能范围

1. Project 实体。
2. Topic 实体。
3. Paper 与 Project 关联。
4. 研究问题管理。
5. 方法卡片。
6. 数据集卡片。
7. Idea Bank。
8. Roadmap 视图。

### 完成标准

1. 每个课题可以绑定相关论文。
2. 每篇论文可以标记 project relevance。
3. 可以从论文笔记进入课题页面。
4. 可以查看课题论文覆盖情况。

## 7. M5 桌面封装

### 目标

在 Web 版本稳定后，封装为桌面软件。

### 可选方案

| 方案 | 优点 | 适用阶段 |
|---|---|---|
| Electron | 生态成熟，打包资料多 | 功能稳定后 |
| Tauri | 轻量，资源占用小 | 对打包复杂度可接受时 |
| Web Only | 简单，便于本地和服务器部署 | 默认形态 |

### 推荐路线

```text
本地 Web MVP
继续完善 Web
Electron 或 Tauri 封装
```

桌面壳只负责启动前端和本地后端，不重写业务逻辑。

## 8. 版本规划

| 版本 | 名称 | 核心目标 |
|---|---|---|
| v0.1 | Prototype | 静态 Dashboard 与数据模型验证 |
| v0.2 | MVP | Paper CRUD、Search Batch、Curated、Library |
| v0.3 | Pipeline | PDF 解析、分类审核、任务队列 |
| v0.4 | Obsidian Export | Markdown 导出与 Dataview 页面 |
| v0.5 | Research Project | Project、Topic、Paper 关联 |
| v1.0 | Local Research Workbench | 稳定本地科研工作台 |
