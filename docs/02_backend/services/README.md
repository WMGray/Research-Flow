---
title: Backend Services 说明
status: active
updated: 2026-05-14
---

# Backend Services

当前 `backend/core/services/` 只正式承载 `papers/`。第一阶段所有服务都围绕 Paper 全流程，不拆出 Project / Dataset / Knowledge。

## `papers/`

### `models.py`

- 定义 `PaperRecord`
- 定义 `BatchRecord`
- 定义 CLI / API 共用输入模型

### `repository.py`

- 面向文件系统的真源实现
- 扫描 `data/`
- 解析 metadata
- 执行 ingest / migrate

### `service.py`

- 面向 API 与 CLI 的薄服务层
- 聚合 dashboard 数据
- 保持接口语义稳定

### `utils.py`

- YAML / JSON / markdown front matter 工具
- slugify
- metadata merge

### `parser.py`

- 程序式 PDF parser 编排
- 读取 `paper.pdf`
- 写入 `parsed/` 产物
- 更新 parser run JSON 状态

### `config.py`

- 暴露当前数据根
- 检查 `Discover / Acquire / Library / templates` 路径健康
- 为后续用户指定数据目录预留入口
