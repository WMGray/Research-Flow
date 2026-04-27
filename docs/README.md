# Research-Flow 文档中心

## 定位

`docs/` 只保存长期设计、方案、接口契约、服务接入指导和外部参考资料。

不放入 `docs/` 的内容：

- 测试报告、联网探针报告、一次性审计记录：放入 `reports/`（已 gitignore）。
- 运行时数据、pytest 临时目录、机器生成 JSON：放入 `backend/data/tmp/`。
- 只有标题和“待补充”的空占位文档：等需要真实方案时再创建。

## 目录结构

```
docs/
├── README.md
├── 00_overview/                 ← 项目总览与需求
│   ├── 用户需求文档.md
│   ├── 产品需求文档.md
│   └── 路线图.md
├── 02_backend/                  ← 后端架构、模块、表与长期测试方案
│   ├── 架构概览.md
│   ├── 数据模型.md
│   ├── 表设计.md
│   ├── Paper链路测试方案.md
│   ├── modules/
│   │   ├── 文献管理.md
│   │   └── 课题管理.md
│   └── services/
│       ├── README.md
│       ├── pdf-parser.md
│       ├── zotero-mcp.md
│       ├── llm/
│       │   └── minimax.md
│       └── cloud/
│           └── aliyun.md
├── 03_api/
│   └── 接口规范.md
└── 04_reference/                ← 外部参考与前端参考素材
    ├── README.md
    ├── claude-scholar分析.md
    └── frontend/
        ├── screenshots/
        └── html/
```

## 各目录职责

| 目录 | 受众 | 回答的问题 |
|------|------|-----------|
| `00_overview` | 全员 | 产品是什么、做什么、做到哪 |
| `02_backend` | 后端开发 | 每个模块的业务逻辑、数据结构、外部服务与第三方集成 |
| `03_api` | 前后端共同维护 | 前后端如何对接、接口格式 |
| `04_reference` | 全员 | 参考了什么、为什么这样设计 |

说明：

- `01_frontend/` 当前不保留空占位；未来有真实页面方案、交互规范或设计系统文档时再创建。
- 前端截图、HTML 原型等参考素材统一放在 `04_reference/frontend/`，不混入前端方案目录。
- 状态类和报告类资料统一放在 `reports/`，不作为长期设计依据提交到仓库。
