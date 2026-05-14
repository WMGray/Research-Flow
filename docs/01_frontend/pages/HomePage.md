---
title: HomePage 页面说明
status: active
updated: 2026-05-14
---

# HomePage 页面说明

## 1. 页面职责

HomePage 是当前唯一完成的真实页面，用于承接 Paper 全流程的总入口。

## 2. 信息结构

- 顶部导航
- Hero 区域
- 文献总体统计卡片
- 研究信息与状态分布
- 会议时间占位区
- 待处理队列
- Dashboard 跳转入口
- Recent batches

## 3. 数据来源

接口：`GET /api/dashboard/home`

关键字段：

- `totals`
- `status_counts`
- `recent_papers`
- `queue_items`
- `recent_batches`
- `paths`

## 4. 当前实现限制

- 会议信息仍为前端静态占位
- Discover / Acquire / Library 详情页尚未接通
- 首页不提供编辑能力，只承担汇总和跳转

## 5. 下一步调整

- 将首页跳转与 Discover / Acquire / Library / Config 路由对齐。
- 待处理队列需要区分 `needs-pdf`、`needs-review`、`parse-failed`。
- 首页只展示摘要，不承载 PDF 解析、元数据编辑或路径配置。
