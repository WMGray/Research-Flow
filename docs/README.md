---
title: Research-Flow 文档中心
status: active
updated: 2026-05-14
---

# Research-Flow 文档中心

`docs/` 采用与 `origin/master` 对齐的分层结构，但当前只保留 Paper 全流程第一阶段需要落地的内容。

当前定制结论：

- 第一阶段只做 Paper 全流程，不展开 Project / Dataset / Knowledge / Presentation。
- 根目录 `data/` 是唯一数据真源；软件完成后再支持用户指定数据根目录。
- 暂不引入数据库，使用 JSON / Markdown / PDF 等文件状态暂存。
- 暂不做 LLM Provider 与 Agent 自动编排，涉及判断的节点先交给人工。
- Paper 流程中实际需要的程序式能力必须落地，包括 PDF parser、产物索引和状态追踪。
- 方案以可维护为目标，`origin/master` 的大方案只做提炼，不全量搬回。

## 目录结构

```text
docs/
├─ README.md
├─ 00_overview/
│  ├─ 用户需求文档.md
│  ├─ 产品需求文档.md
│  └─ 路线图.md
├─ 01_frontend/
│  ├─ 架构概览.md
│  └─ pages/
│     ├─ HomePage.md
│     ├─ Discover.md
│     ├─ Acquire.md
│     ├─ Library.md
│     ├─ PaperDetail.md
│     └─ Config.md
├─ 02_backend/
│  ├─ 架构概览.md
│  ├─ 数据模型.md
│  ├─ Paper链路测试方案.md
│  ├─ modules/
│  │  └─ 文献管理.md
│  └─ services/
│     ├─ README.md
│     └─ pdf-parser.md
├─ 03_api/
│  └─ 接口规范.md
└─ 04_reference/
   ├─ README.md
   └─ frontend/
      └─ screenshots/
```

## 阅读顺序

1. `00_overview/`：看 Paper 全流程范围、阶段目标和取舍。
2. `01_frontend/`：看 Discover / Acquire / Library / Paper Detail / Config 页面边界。
3. `02_backend/`：看后端分层、文件系统文献库、JSON 状态与 PDF parser 链路。
4. `03_api/`：看当前接口与下一步接口契约。
5. `04_reference/`：看 UI 参考图和流程截图。

## 当前原则

- `docs/` 只放长期有效的需求、架构、接口、页面边界与参考资料。
- 运行日志、测试临时结果、一次性调研结论不放进 `docs/`。
- 本轮只覆盖 Paper 全流程，不为平台后续能力写大量空文档。
- 后续能力只保留到路线图层级，等进入实施阶段再展开详细设计。
