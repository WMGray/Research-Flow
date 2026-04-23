# Research-Flow 文档中心

## 目录结构

````
docs/
├── README.md                    ← 本文件
├── 需求.md                      ← 原始需求草稿（存档只读）
├── 00_overview/                 ← 项目总览（全员必读）
│   ├── 用户需求文档.md
│   ├── 产品需求文档.md
│   └── 路线图.md
├── 01_frontend/                 ← 前端需求
│   ├── 页面清单.md
│   ├── 交互设计.md
│   └── pages/
│       ├── Dashboard.md
│       ├── Daily.md
│       ├── Datasets.md
│       ├── Library.md
│       ├── Projects.md
│       └── Views.md
├── 02_backend/                  ← 后端需求
│   ├── 架构概览.md
│   ├── 数据模型.md
│   ├── 表设计.md
│   ├── modules/
│   │   ├── 文献管理.md
│   │   ├── Zotero集成.md
│   │   ├── 每日推送.md
│   │   ├── 数据集管理.md
│   │   ├── 观点提炼.md
│   │   ├── 实验规划.md
│   │   ├── 课题管理.md
│   │   ├── 论文写作.md
│   │   ├── 知识图谱.md
│   │   ├── 会议追踪.md
│   │   └── 定时任务.md
│   └── services/                ← 第三方服务接入文档
│       ├── README.md
│       ├── zotero-mcp.md
│       ├── llm/
│       │   └── minimax.md
│       └── cloud/
│           └── aliyun.md
├── 03_api/                      ← 前后端接口文档
│   ├── 接口规范.md
│   └── endpoints/
│       ├── 文献管理.md
│       ├── 每日推送.md
│       ├── 数据集管理.md
│       ├── 课题管理.md
│       ├── 知识图谱.md
│       └── 会议追踪.md
└── 04_reference/                ← 外部参考资料
    ├── README.md
    ├── claude-scholar分析.md
    └── 竞品分析.md
````

## 各目录职责

| 目录 | 受众 | 回答的问题 |
|------|------|-----------|
| `00_overview` | 全员 | 产品是什么、做什么、做到哪 |
| `01_frontend` | 前端开发 | 每个页面长什么样、怎么交互 |
| `02_backend` | 后端开发 | 每个模块的业务逻辑、数据结构、外部服务与第三方集成 |
| `03_api` | 前后端共同维护 | 前后端如何对接、接口格式 |
| `04_reference` | 全员 | 参考了什么、为什么这样设计 |