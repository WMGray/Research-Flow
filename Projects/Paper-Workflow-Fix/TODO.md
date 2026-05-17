---
title: 今晚待做 - Paper 流程修复
updated: 2026-05-15 03:15:00
status: done
tags:
  - paper
  - workflow
  - backend
  - frontend
---

# 今晚目标

- [x] 把当前 `Paper` 主流程修成真正闭环：`Discover -> Acquire -> Library -> Paper Detail`
- [x] 本轮只解决 `Paper` 流程本身，不扩展 `Project / Dataset / LLM`

# 已完成

## P0-1. 统一契约：状态模型 + 动作能力 + 命令语义

- [x] 新增 `stage`
- [x] 新增 `asset_status`
- [x] 新增 `parser_status`
- [x] 新增 `review_status`
- [x] 新增 `note_status`
- [x] 新增 `parser_artifacts`
- [x] 新增 `capabilities`
- [x] 保留旧 `status` / `mark-review` / `mark-processed` 作为兼容层
- [x] 统一“已解析”真源为 `parser_status == parsed`
- [x] 允许 `PyMuPDF` 只有 `text + sections` 时也视为 `parsed`

## P0-2. 打通后端主链路

- [x] 新增 `POST /api/papers/{paper_id}/accept`
- [x] 新增 `accept_paper(...)`
- [x] 新增 `promote_to_library(...)`
- [x] `Acquire -> Library` 现在是真迁移，不再只是改状态
- [x] 迁移后重算 `stage / path / paper_id / status / capabilities`
- [x] `reject` 继续物理删除
- [x] Dashboard 去掉 `rejected`

## P1-1. 收前端 Workflow / Detail / Library

- [x] 删除 `Acquire` 页 `Add Curated Paper`
- [x] 删除 `transferPaper` 相关入口和状态
- [x] `Acquire` 页 `Accept` 改调新 `accept` 接口
- [x] 按钮禁用逻辑改用 `capabilities`
- [x] 主流程 badge 改用新状态字段
- [x] 文件产物显示改用 `parser_artifacts`
- [x] 前端不再靠“路径非空”或旧 `status` 猜动作可用性

## P1-2. 测试与验证

- [x] 补 `accept -> moved into library` 后端测试
- [x] 补 `capabilities` 判定测试
- [x] 补 `PyMuPDF` 仅产出 `text + sections` 的状态测试
- [x] `python -m pytest backend/tests/test_api.py backend/tests/test_library.py`
- [x] `npm run lint`
- [x] `npm run build`

## P2. 文档和收尾

- [x] 更新 `docs/03_api/接口规范.md`
- [x] 更新 `backend/README.md`
- [x] 清理前端旧入口和旧判断逻辑

# 验收结果

- [x] `Acquire -> Library` 真迁移已打通
- [x] Acquire 页面已移除手工入库入口
- [x] Dashboard 已去掉 `reject` 统计
- [x] 前端动作可用性已改为后端驱动
- [x] 解析完成不再用“路径非空”硬判断
- [x] 核心流程测试已通过

# 备注

- [x] `reject` 继续物理删除，不做归档
- [x] 旧接口仍保留一轮兼容，但主流程已切换到新契约
