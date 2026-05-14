---
title: Library 页面说明
status: draft
updated: 2026-05-14
---

# Library 页面说明

## 1. 页面职责

Library 展示正式文献库，是已入库论文的主要浏览和筛选入口。

## 2. 信息结构

- 论文列表
- domain / area / topic 筛选
- 状态筛选
- PDF / note / parsed 产物标记
- 跳转 Paper Detail

## 3. 数据来源

- `GET /api/dashboard/library`
- `GET /api/papers`

## 4. 边界

- 不在列表页做复杂编辑。
- 不在列表页展示完整 parser 产物。
- 批量操作只保留轻量入口，具体确认进入详情页。
