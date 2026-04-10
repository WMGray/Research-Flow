.PHONY: help init dev dev-backend dev-frontend install install-backend install-frontend lint fmt clean

# 默认目标：显示帮助
help:
	@echo ""
	@echo "Research-Flow 开发命令"
	@echo "========================"
	@echo "  make init              初始化完整开发环境"
	@echo "  make dev               同时启动前后端开发服务"
	@echo "  make dev-backend       仅启动后端服务"
	@echo "  make dev-frontend      仅启动前端服务"
	@echo "  make install           安装前后端全部依赖"
	@echo "  make install-backend   安装后端依赖"
	@echo "  make install-frontend  安装前端依赖"
	@echo "  make lint              检查前后端代码风格"
	@echo "  make fmt               格式化前后端代码"
	@echo "  make clean             清理构建产物与缓存"
	@echo ""

# 初始化开发环境（首次克隆后执行）
init:
	@echo ">>> 初始化开发环境..."
	@if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; echo ">>> 已生成 backend/.env，请填写必要配置"; fi
	@$(MAKE) install
	@echo ">>> 初始化完成"

# 同时启动前后端（需要系统安装 concurrently 或 make 支持并行）
dev:
	@echo ">>> 启动前后端开发服务..."
	@$(MAKE) -j2 dev-backend dev-frontend

# 仅启动后端
dev-backend:
	@echo ">>> 启动后端..."
	cd backend && python -m uvicorn app.main:app --reload --port 8000

# 仅启动前端
dev-frontend:
	@echo ">>> 启动前端..."
	cd frontend && npm run dev

# 安装全部依赖
install: install-backend install-frontend

# 安装后端依赖
install-backend:
	@echo ">>> 安装后端依赖..."
	cd backend && pip install -r requirements.txt

# 安装前端依赖
install-frontend:
	@echo ">>> 安装前端依赖..."
	cd frontend && npm install

# 代码风格检查
lint:
	@echo ">>> 检查后端代码..."
	cd backend && ruff check .
	@echo ">>> 检查前端代码..."
	cd frontend && npm run lint

# 代码格式化
fmt:
	@echo ">>> 格式化后端代码..."
	cd backend && ruff format .
	@echo ">>> 格式化前端代码..."
	cd frontend && npm run fmt

# 清理构建产物与缓存
clean:
	@echo ">>> 清理中..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist frontend/.vite 2>/dev/null || true
	@echo ">>> 清理完成"
