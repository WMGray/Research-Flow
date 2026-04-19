# Backend Config

当前后端配置通过 `pydantic-settings` 加载，默认优先级如下：

1. `Settings(...)` 初始化参数
2. 系统环境变量
3. `backend/.env`
4. `backend/config/settings.toml`

推荐约定：

- `settings.toml` 存放可提交的非敏感默认值
- `.env` 存放本机密钥和本地覆盖
- 需要切换配置文件时，设置 `RESEARCH_FLOW_CONFIG_FILE`

当前实现位置：

- `app/core/config.py`
- `config/settings.toml`

Zotero 配置兼容两类环境变量：

- 扁平命名，例如 `ZOTERO_MCP_TIMEOUT_SECONDS`
- 嵌套命名，例如 `ZOTERO__TIMEOUT_SECONDS`
