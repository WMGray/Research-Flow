---
title: Research-Flow 文档中心
status: draft
updated: 2026-05-14
---

# Research-Flow 文档中心

## 文档分工

| 文件 | 作用 |
| --- | --- |
| `01_需求与范围.md` | 说明 Paper MVP 的业务目标、边界与优先级 |
| `02_架构与流程.md` | 说明前后端分离架构、`data/` 目录和状态流转 |
| `03_API_与实施.md` | 说明当前 FastAPI 接口、脚本命令和验收方式 |

## 当前实现基线

1. 前后端分离，目录形态参考 `origin/master`。
2. 后端使用 FastAPI + 文件系统，不接 Celery、Redis、skills。
3. `data/` 是唯一主存储位置。
4. 前端当前只落地 HomePage 与基础路由壳。

