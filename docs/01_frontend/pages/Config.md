---
title: Config 页面说明
status: draft
updated: 2026-05-14
---

# Config 页面说明

## 1. 页面职责

Config 展示当前本地运行配置，并为后续用户指定数据存放地点预留入口。

## 2. 信息结构

- 当前数据根
- `Discover / Acquire / Library / templates` 路径健康
- parser 可用性
- 默认分类配置
- 后续外部数据根设置入口

## 3. 数据来源

- `GET /api/config`
- 后续可补 `PUT /api/config/data-root`

## 4. 边界

- 当前阶段数据根固定为仓库根 `data/`。
- 暂不做多 profile 配置。
- 暂不保存 API key、token 或 LLM Provider 配置。
