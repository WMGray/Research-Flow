---
title: Discover 页面说明
status: draft
updated: 2026-05-14
---

# Discover 页面说明

## 1. 页面职责

Discover 展示搜索批次和候选论文，是 Paper 全流程的入口。

## 2. 信息结构

- 搜索批次列表
- 批次统计
- 候选论文列表
- keep / reject 状态
- 进入 Acquire 的操作入口

## 3. 数据来源

- `GET /api/dashboard/discover`
- 后续可补 `GET /api/discover/batches`

## 4. 边界

- 不做真实联网搜索。
- 不做 LLM 自动筛选。
- 当前只展示已有批次和人工选择结果。
