# Backend Config

当前后端配置通过 `pydantic-settings` 加载，默认优先级如下：

1. `Settings(...)` 初始化参数
2. 系统环境变量
3. `backend/.env`
4. `backend/config/settings.toml`

推荐约定：

- `settings.toml` 存放可提交的非敏感默认值
- `.env` 只存放本机密钥和必要的本地覆盖
- 已经迁移到 `settings.toml` 的默认项不要在 `.env.example` 里重复列出
- 需要切换配置文件时，设置 `RESEARCH_FLOW_CONFIG_FILE`
- 需要跳过本机 `.env` 时，设置 `RESEARCH_FLOW_ENV_FILE=none`

当前实现位置：

- `core/config.py`
- `config/settings.toml`

配置兼容两类环境变量：

- 扁平命名，例如 `ZOTERO_MCP_TIMEOUT_SECONDS`、`RFLOW_MINERU_API_TOKEN`、`PDF_PARSER_MARKDOWN_REFINE_ENABLED`
- 嵌套命名，例如 `ZOTERO__TIMEOUT_SECONDS`、`MINERU__API_TOKEN`

当前已显式兼容的历史扁平命名覆盖范围：

- `APP_*`
- `ZOTERO_*`
- `PAPER_DOWNLOAD_*` / `EXTRACT_REFS_*`
- `RFLOW_MINERU_*` / `RFLOW_PDF_*`
- `PDF_PARSER_MARKDOWN_REFINE_*`
