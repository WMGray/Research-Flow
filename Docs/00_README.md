---
updated: 2026-05-14 01:25:03
---

# PaperFlow 项目文档总览

## 项目定位

PaperFlow 是一个面向科研场景的论文与课题管理工具，目标是把论文发现、候选筛选、PDF 管理、解析入库、分类审核、阅读笔记、课题关联和 Dashboard 总览整合到一个本地优先的研究工作台中。

第一版建议采用本地 Web 应用形态：

```text
前端：React 或 Vue
后端：FastAPI
数据库：SQLite
文件存储：本地文件系统
后台任务：Python Worker，后续升级 Celery 或 RQ
导出对象：Obsidian Vault / Markdown / PDF 资产目录
```

## 文档结构

| 文档 | 作用 |
|---|---|
| `01_PRD_需求规格说明.md` | 定义目标用户、核心问题、需求范围、功能优先级、验收标准 |
| `02_Roadmap_总路线.md` | 定义 MVP 到桌面封装的阶段路线、里程碑和交付物 |
| `03_System_Design_系统设计方案.md` | 定义系统架构、模块边界、前后端分工、文件存储方案 |
| `04_Data_Model_数据模型与状态机.md` | 定义 Paper、Project、Task、Note、Metadata、状态流转 |
| `05_UI_IA_信息架构与页面设计.md` | 定义页面结构、Dashboard、交互语义和关键视图 |
| `06_Pipeline_任务队列与处理流程.md` | 定义检索、解析、分类、笔记生成、导出等后台流程 |
| `07_API_Draft_API草案.md` | 定义后端 API 草案，便于前后端并行开发 |
| `08_Acceptance_Test_验收与测试.md` | 定义 MVP 验收标准、测试用例和质量门槛 |
| `09_Codex_Tasks_Codex实施任务.md` | 将需求拆成可交给 Codex 执行的工程任务 |

## 第一版总原则

1. 本地优先，所有核心数据可离线访问。
2. Web 优先，桌面封装后置。
3. 文件系统与 SQLite 双轨管理，文件可独立浏览，数据库负责检索与状态。
4. LLM 只给建议，关键迁移与分类由用户确认。
5. Dashboard 展示状态，具体处理进入阶段页面。
6. 不追求一开始覆盖全部科研知识管理，先跑通论文闭环。
