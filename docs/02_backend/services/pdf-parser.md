---
title: PDF Parser 设计
status: draft
updated: 2026-05-14
---

# PDF Parser 设计

## 1. 定位

PDF parser 是 Paper 全流程的必需能力。它负责把 `paper.pdf` 转换为可查看、可索引、可复用的程序式产物。

本阶段 parser 不依赖 LLM Provider，不做自动学术判断，只做确定性解析、失败记录和产物管理。

## 2. 输入输出

输入：

- `paper_id`
- `paper.pdf`
- parser options
- `force` 是否覆盖旧解析结果

输出：

- `parsed/text.md`
- `parsed/sections.json`
- `parsed/images/`
- `parser_runs.json`
- `metadata.json` 中的 `parser_status`

## 3. 状态

- `pending`：等待解析。
- `running`：解析中。
- `succeeded`：关键产物生成成功。
- `failed`：解析失败，错误可查看。
- `needs-review`：产物存在但需要人工确认。

## 4. 错误处理

- 缺少 `paper.pdf`：Paper 状态改为 `needs-pdf`。
- PDF 无法读取：parser run 改为 `failed`。
- 章节结构不可靠：parser run 改为 `needs-review`。
- 已有解析产物且未设置 `force`：不覆盖旧产物。

## 5. API / CLI

建议接口：

- `POST /api/papers/{paper_id}/parse-pdf`
- `GET /api/papers/{paper_id}/parser-runs`

建议 CLI：

```bash
python -m backend.scripts.paper_library parse-pdf --paper-id <paper_id>
python -m backend.scripts.paper_library parse-pdf --paper-id <paper_id> --force
```

## 6. 人工边界

parser 只生成候选结构。以下判断由人工完成：

- 章节是否准确。
- 图表是否需要保留。
- note 是否采用 parser 结果。
- 是否需要重新解析或手工修正。
