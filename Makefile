.PHONY: help init dev dev-all dev-backend dev-frontend dev-worker dev-beat \
        install install-backend install-frontend \
        lint fmt clean

# 默认目标：显示帮助
help:
	@echo ""
	@echo "Research-Flow 开发命令"
	@echo "========================"
	@echo "  make init              初始化完整开发环境（首次克隆后执行）"
	@echo ""
	@echo "  启动服务"
	@echo "  --------"
	@echo "  make dev               同时启动前后端（不含 Celery）"
	@echo "  make dev-all           同时启动全部服务（前后端 + Worker + Beat）"
	@echo "  make dev-backend       仅启动 FastAPI 后端"
	@echo "  make dev-frontend      仅启动前端"
	@echo "  make dev-worker        仅启动 Celery Worker（执行异步任务）"
	@echo "  make dev-beat          仅启动 Celery Beat（定时任务调度）"
	@echo ""
	@echo "  依赖管理"
	@echo "  --------"
	@echo "  make install           安装前后端全部依赖"
	@echo "  make install-backend   安装后端依赖（uv sync）"
	@echo "  make install-frontend  安装前端依赖（npm install）"
	@echo ""
	@echo "  代码质量"
	@echo "  --------"
	@echo "  make lint              检查前后端代码风格"
	@echo "  make fmt               格式化前后端代码"
	@echo "  make clean             清理构建产物与缓存"
	@echo ""

# ------------------------------------------------------------
# 初始化开发环境（首次克隆后执行）
# ------------------------------------------------------------
init:
	@echo ">>> 初始化开发环境..."
	@if [ ! -f backend/.env ]; then \
		cp backend/.env.example backend/.env; \
		echo ">>> 已生成 backend/.env，请填写 LLM API Key 等配置"; \
	fi
	@if [ ! -f frontend/.env ]; then \
		cp frontend/.env.example frontend/.env; \
		echo ">>> 已生成 frontend/.env，如有需要请修改 API 地址"; \
	fi
	@$(MAKE) install
	@echo ">>> 初始化完成"

# ------------------------------------------------------------
# 启动服务
# ------------------------------------------------------------

# 同时启动前后端（不含 Celery）
dev:
	@echo ">>> 启动前后端开发服务..."
	@$(MAKE) -j2 dev-backend dev-frontend

# 同时启动全部服务（前后端 + Worker + Beat）
dev-all:
	@echo ">>> 启动全部开发服务..."
	@$(MAKE) -j4 dev-backend dev-frontend dev-worker dev-beat

# 仅启动 FastAPI 后端
dev-backend:
	@echo ">>> 启动 FastAPI 后端..."
	cd backend && uv run uvicorn app.main:app --reload --port 8000

# 仅启动前端
dev-frontend:
	@echo ">>> 启动前端..."
	cd frontend && npm run dev

# 仅启动 Celery Worker（执行异步任务）
dev-worker:
	@echo ">>> 启动 Celery Worker..."
	cd backend && uv run celery -A worker.app worker --loglevel=info

# 仅启动 Celery Beat（定时任务调度，全局只能运行一个实例）
dev-beat:
	@echo ">>> 启动 Celery Beat..."
	cd backend && uv run celery -A worker.app beat --loglevel=info

# ------------------------------------------------------------
# 依赖管理
# ------------------------------------------------------------

# 安装全部依赖
install: install-backend install-frontend

# 安装后端依赖（uv workspace 会同时同步 worker 包）
install-backend:
	@echo ">>> 安装后端依赖..."
	cd backend && uv sync --all-packages

# 安装前端依赖
install-frontend:
	@echo ">>> 安装前端依赖..."
	cd frontend && npm install

# ------------------------------------------------------------
# 代码质量
# ------------------------------------------------------------

# 代码风格检查
lint:
	@echo ">>> 检查后端代码..."
	cd backend && uv run ruff check .
	@echo ">>> 检查前端代码..."
	cd frontend && npm run lint

# 代码格式化
fmt:
	@echo ">>> 格式化后端代码..."
	cd backend && uv run ruff format .
	@echo ">>> 格式化前端代码..."
	cd frontend && npm run fmt

# ------------------------------------------------------------
# 清理
# ------------------------------------------------------------
clean:
	@echo ">>> 清理中..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"   -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist frontend/.vite 2>/dev/null || true
	@echo ">>> 清理完成"
