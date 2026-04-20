.PHONY: help init dev dev-backend dev-frontend install install-backend install-frontend test-paper-download lint fmt clean

# Show common development commands.
help:
	@echo ""
	@echo "Research-Flow commands"
	@echo "======================"
	@echo "  make init                 Initialize development environment"
	@echo "  make dev                  Start backend and frontend"
	@echo "  make dev-backend          Start backend only"
	@echo "  make dev-frontend         Start frontend only"
	@echo "  make install              Install all dependencies"
	@echo "  make install-backend      Install backend dependencies"
	@echo "  make install-frontend     Install frontend dependencies"
	@echo "  make test-paper-download  Run gPaper paper_download check"
	@echo "  make lint                 Run linters"
	@echo "  make fmt                  Format code"
	@echo "  make clean                Clean generated artifacts"
	@echo ""

# Initialize local development environment.
init:
	@echo ">>> Initializing development environment..."
	@if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; echo ">>> Created backend/.env; please fill required values"; fi
	@$(MAKE) install
	@echo ">>> Initialization complete"

# Start backend and frontend in parallel.
dev:
	@echo ">>> Starting backend and frontend..."
	@$(MAKE) -j2 dev-backend dev-frontend

# Start backend only.
dev-backend:
	@echo ">>> Starting backend..."
	cd backend && python -m uvicorn app.main:app --reload --port 8000

# Start frontend only.
dev-frontend:
	@echo ">>> Starting frontend..."
	cd frontend && npm run dev

# Install all dependencies.
install: install-backend install-frontend

# Install backend dependencies.
install-backend:
	@echo ">>> Installing backend dependencies..."
	cd backend && pip install -r requirements.txt

# Install frontend dependencies.
install-frontend:
	@echo ">>> Installing frontend dependencies..."
	cd frontend && npm install

# Manual gPaper / paper_download integration check.
test-paper-download:
	cd backend && python tests/run_paper_download_cases.py --case direct_pdf

# Run code style checks.
lint:
	@echo ">>> Checking backend code..."
	cd backend && ruff check .
	@echo ">>> Checking frontend code..."
	cd frontend && npm run lint

# Format code.
fmt:
	@echo ">>> Formatting backend code..."
	cd backend && ruff format .
	@echo ">>> Formatting frontend code..."
	cd frontend && npm run fmt

# Clean generated artifacts.
clean:
	@echo ">>> Cleaning..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist frontend/.vite 2>/dev/null || true
	@echo ">>> Clean complete"
