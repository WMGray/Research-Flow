# Research-Flow Frontend

基于 **React + TypeScript + Vite** 的科研工作流管理平台前端应用。

## 技术栈

| 类别 | 技术选型 | 说明 |
|------|---------|------|
| 框架 | React 19 | UI 渲染框架 |
| 语言 | TypeScript 5.7 | 全量类型覆盖 |
| 构建工具 | Vite 6 | 开发服务器与构建 |
| 路由 | React Router 7 | 客户端路由管理 |
| 全局状态 | Zustand 5 | 轻量全局状态管理 |
| 服务端状态 | TanStack Query 5 | 接口请求、缓存、同步 |
| HTTP 客户端 | Axios 1.7 | 请求封装与拦截器 |
| 代码规范 | ESLint 9 + Prettier 3 | 风格检查与格式化 |

---

## 目录结构

```
frontend/
├── public/                 # 静态资源（favicon、字体等，直接复制到构建产物）
│
├── src/
│   ├── api/                # 接口请求层
│   │                       #   · axios 实例与拦截器配置
│   │                       #   · 按业务模块划分的请求函数
│   │
│   ├── assets/             # 本地资源（图片、SVG、字体等，经 Vite 处理）
│   │
│   ├── components/         # 全局公共组件（无业务含义、跨模块复用）
│   │   ├── ui/             #   基础 UI 原子组件（Button、Modal、Table 等）
│   │   ├── editor/         #   Markdown 编辑器封装
│   │   └── graph/          #   知识图谱可视化封装
│   │
│   ├── features/           # 业务功能模块（按需拆分，后续逐步填充）
│   │   └── {module}/
│   │       ├── components/ #   该模块专属组件
│   │       ├── hooks/      #   该模块专属 Hooks
│   │       ├── types.ts    #   该模块 TypeScript 类型
│   │       └── index.ts    #   统一导出，外部只从这里 import
│   │
│   ├── hooks/              # 全局公共 Hooks（与业务无关的通用逻辑）
│   ├── layouts/            # 页面布局骨架（侧边栏、顶栏、内容区等）
│   ├── pages/              # 路由级页面组件（组合 features，不写业务逻辑）
│   ├── router/             # React Router 路由配置
│   ├── stores/             # Zustand 全局状态（跨模块共享的状态）
│   ├── types/              # 全局 TypeScript 类型定义
│   ├── utils/              # 纯工具函数（格式化、日期处理等）
│   ├── App.tsx             # 根组件，挂载 RouterProvider
│   └── main.tsx            # 应用入口，挂载到 #root
│
├── .env                    # 本地环境变量（不提交 Git）
├── .env.example            # 环境变量配置模板
├── index.html              # Vite HTML 入口
├── package.json            # 依赖管理与脚本命令
├── tsconfig.json           # 应用代码 TypeScript 配置
├── tsconfig.node.json      # Vite 配置文件自身的 TypeScript 配置
└── vite.config.ts          # Vite 构建配置
```

---

## 分层设计

### 数据流向

```
用户操作
    │
    ▼
┌──────────────────────────────────────┐
│  pages/           路由级页面          │
│  · 只做布局组合，不写业务逻辑          │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  features/{module}/  业务模块         │
│  · components：该模块的 UI 组件        │
│  · hooks：数据获取与本地状态           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  api/         接口请求层              │
│  · 封装 axios，统一处理 token、错误    │
│  · 各模块请求函数，对接后端 REST API   │
└──────────────────────────────────────┘
```

### 状态管理策略

| 状态类型 | 工具 | 说明 |
|---------|------|------|
| 服务端数据 | TanStack Query | 接口数据、缓存、自动刷新 |
| 全局 UI 状态 | Zustand | 侧边栏折叠、主题、全局通知等 |
| 局部组件状态 | useState / useReducer | 表单、弹窗开关等组件内状态 |

> 优先用 TanStack Query 管理服务端数据，只有真正需要跨组件共享的 UI 状态才放入 Zustand。

---

## 路径别名

`@/` 指向 `src/`，在 `tsconfig.json` 与 `vite.config.ts` 中均已配置：

```ts
// 使用别名，避免相对路径地狱
import { Button } from '@/components/ui'
import { usepapers } from '@/features/papers'
```

---

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 按需修改 VITE_API_BASE_URL
```

### 2. 安装依赖

```bash
npm install
```

### 3. 启动开发服务

```bash
npm run dev
# 访问 http://localhost:5173
```

> 开发服务器已配置 `/api` 代理，所有 `/api/*` 请求自动转发到后端 `http://localhost:8000`，无需处理跨域。

### 4. 其他命令

```bash
npm run build     # 生产构建，产物输出到 dist/
npm run preview   # 预览生产构建结果
npm run lint      # ESLint 代码检查
npm run fmt       # Prettier 代码格式化
```

---

## 环境变量说明

完整配置项见 [`.env.example`](./.env.example)：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 地址 | `http://localhost:8000` |
| `VITE_APP_TITLE` | 页面标题 | `Research-Flow` |

> Vite 中只有以 `VITE_` 开头的变量才会暴露给客户端代码。