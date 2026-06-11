.PHONY: help \
        fe-install fe-dev fe-build fe-test fe-lint \
        be-install be-test be-lint be-format \
        db-up db-down db-migrate \
        up down health \
        clean

FRONTEND_DIR := apps/frontend
BACKEND_DIR  := apps/backend

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Frontend ─────────────────────────────────────────────────────────────────

FE_MODULES := $(FRONTEND_DIR)/node_modules

$(FE_MODULES): $(FRONTEND_DIR)/package.json $(FRONTEND_DIR)/package-lock.json
	cd $(FRONTEND_DIR) && npm install
	touch $(FE_MODULES)

fe-install: $(FE_MODULES) ## Install frontend dependencies (skipped when up-to-date)

fe-dev: $(FE_MODULES) ## Start frontend dev server
	cd $(FRONTEND_DIR) && npm run dev

fe-build: $(FE_MODULES) ## Build frontend for production
	cd $(FRONTEND_DIR) && npm run build

fe-test: $(FE_MODULES) ## Run frontend tests
	cd $(FRONTEND_DIR) && npm test

fe-lint: $(FE_MODULES) ## Lint frontend
	cd $(FRONTEND_DIR) && npm run lint

# ── Backend ──────────────────────────────────────────────────────────────────

be-install: ## Install backend dependencies
	cd $(BACKEND_DIR) && uv sync

be-test: ## Run backend tests
	cd $(BACKEND_DIR) && uv run pytest

be-lint: ## Lint backend
	cd $(BACKEND_DIR) && uv run ruff check .

be-format: ## Format backend
	cd $(BACKEND_DIR) && uv run ruff format . && uv run ruff check --fix .

# ── Database ─────────────────────────────────────────────────────────────────

db-up: ## Start database container
	docker compose up db -d

db-down: ## Stop and remove database container
	docker compose down db

db-migrate: ## Run database migrations
	cd $(BACKEND_DIR) && uv run alembic upgrade head

# ── Docker ───────────────────────────────────────────────────────────────────

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

health: ## Check backend health
	docker compose run --rm app health

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: ## Remove all build/cache artefacts
	rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/.vite
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} +
	find $(BACKEND_DIR) -type d -name .pytest_cache -exec rm -rf {} +
	find $(BACKEND_DIR) -type d -name .ruff_cache  -exec rm -rf {} +
