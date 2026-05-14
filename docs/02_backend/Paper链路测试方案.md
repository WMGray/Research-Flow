---
title: Paper 链路测试方案
status: active
updated: 2026-05-14
---

# Paper 链路测试方案

## 1. 目标

验证当前本地文件系统文献库在 Paper 全流程阶段的核心行为稳定。

## 2. 覆盖范围

- slug 生成
- dashboard 汇总读取
- ingest 生成 note 与 metadata
- 冲突目录不覆盖，改标记 `needs-review`
- migrate 真正移动源目录
- API `health`
- API `dashboard/home`
- API `papers list/detail`
- API `ingest / migrate / generate-note`
- PDF parser 成功生成产物
- PDF parser 失败写入 `parse-failed`
- JSON 状态文件可重复读取
- Config 路径健康检查

## 3. 测试命令

```bash
python -m pytest backend/tests
python -m compileall backend
python -m backend.scripts.paper_library scan
python -m backend.scripts.paper_library parse-pdf --paper-id <paper_id>
```

## 4. 当前结果基线

截至 `2026-05-14`：

- `python -m pytest backend/tests` 通过
- CLI `scan` 通过
- `compileall` 可通过；Windows + OneDrive 场景下偶发 `__pycache__` 权限问题不视为业务失败

## 5. 下一步验收用例

- 给定一个含 `paper.pdf` 的样例目录，parser 能生成 `parsed/text.md` 和 `parsed/sections.json`。
- 给定一个损坏 PDF，parser 不影响其他论文扫描，并写入失败原因。
- 给定一个已存在目标目录的 ingest 请求，系统不覆盖旧文件，并进入 `needs-review`。
- 前端五个页面均能从真实 API 获取数据，不依赖 mock。
