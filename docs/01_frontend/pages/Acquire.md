---
title: Acquire 页面说明
status: draft
updated: 2026-05-14
---

# Acquire 页面说明

## 1. 页面职责

Acquire 管理已经保留但尚未稳定入库的论文队列。

## 2. 信息结构

- curated queue
- `needs-pdf` 队列
- `needs-review` 队列
- 元数据确认
- 入库 / 迁移操作

## 3. 数据来源

- `GET /api/dashboard/acquire`
- `POST /api/papers/ingest`
- `POST /api/papers/migrate`

## 4. 边界

- 页面不直接解析 PDF。
- 页面只触发入库、迁移和人工确认。
- 解析动作进入 Paper Detail。
