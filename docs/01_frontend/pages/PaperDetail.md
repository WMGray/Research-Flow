---
title: Paper Detail 页面说明
status: draft
updated: 2026-05-14
---

# Paper Detail 页面说明

## 1. 页面职责

Paper Detail 是单篇论文的工作台，负责元数据、PDF、解析产物和 note 的集中查看。

## 2. 信息结构

- 基础元数据
- 文件路径与存在性检查
- PDF 预览入口
- parser 状态与运行历史
- `parsed/text.md`
- `parsed/sections.json`
- 图片产物索引
- note 查看与生成入口

## 3. 数据来源

- `GET /api/papers/{paper_id}`
- `POST /api/papers/{paper_id}/parse-pdf`
- `GET /api/papers/{paper_id}/parser-runs`
- `POST /api/papers/generate-note`

## 4. 边界

- 质量判断由人工完成。
- 不接入 LLM 自动总结。
- 不覆盖已有人工 note，除非用户明确确认。
