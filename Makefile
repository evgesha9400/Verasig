.DEFAULT_GOAL := help

BACKEND_DIR := apps/backend
FRONTEND_WORKSPACE := verasig-frontend
MARKETING_WORKSPACE := verasig-marketing
DESIGN_SYSTEM_WORKSPACE := @verasig/design-system

ARGS ?= --help

.PHONY: help doctor env \
        install install-backend install-web \
        check format format-check lint lint-backend lint-web \
        test test-backend test-backend-unit test-backend-integration test-web \
        test-frontend test-marketing test-design-system \
        build build-web build-image \
        js-format js-format-check format-backend format-backend-check \
        dev-frontend dev-marketing \
        db-up db-down migrate db-migrate health \
        up down logs cli \
        clean clean-all \
        fe-install fe-dev fe-build fe-test fe-lint \
        be-install be-test be-lint be-format

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

doctor: ## Verify local developer tools
	@command -v npm >/dev/null
	@command -v uv >/dev/null
	@command -v docker >/dev/null
	@docker compose version >/dev/null
	@echo "OK: required tools are available"

env: ## Create .env from .env.example when missing
	@if [ ! -f .env ]; then cp .env.example .env; fi

# Setup

install: install-web install-backend ## Install all project dependencies

install-web: ## Install JavaScript workspace dependencies
	npm ci

install-backend: ## Install backend dependencies
	cd $(BACKEND_DIR) && uv sync --all-groups

# Quality gates

check: format-check lint test build ## Run the full local verification gate

format: js-format format-backend ## Format JavaScript and Python files

format-check: js-format-check format-backend-check ## Check JavaScript and Python formatting

lint: lint-web lint-backend ## Lint JavaScript workspaces and backend

lint-web: ## Lint all JavaScript workspaces
	npm run lint --workspaces --if-present

lint-backend: ## Lint backend Python
	cd $(BACKEND_DIR) && uv run ruff check .

js-format: ## Format JavaScript workspace files
	npm run format:js

js-format-check: ## Check JavaScript workspace formatting
	npm run format:js:check

format-backend: ## Format backend Python
	cd $(BACKEND_DIR) && uv run ruff format . && uv run ruff check --fix .

format-backend-check: ## Check backend Python formatting
	cd $(BACKEND_DIR) && uv run ruff format --check . && uv run ruff check .

# Tests

test: test-backend test-web ## Run all tests

test-backend: ## Run backend tests
	cd $(BACKEND_DIR) && uv run pytest

test-backend-unit: ## Run backend unit tests
	cd $(BACKEND_DIR) && uv run pytest tests/unit

test-backend-integration: ## Run backend integration tests
	cd $(BACKEND_DIR) && uv run pytest tests/integration

test-web: test-design-system test-frontend test-marketing ## Run all JavaScript workspace tests

test-design-system: ## Run design-system tests
	npm run test --workspace $(DESIGN_SYSTEM_WORKSPACE)

test-frontend: ## Run frontend tests once
	npm run test --workspace $(FRONTEND_WORKSPACE) -- --run

test-marketing: ## Run marketing tests once
	npm run test --workspace $(MARKETING_WORKSPACE) -- --run

# Builds

build: build-web build-image ## Build web apps and backend image

build-web: ## Build frontend and marketing apps
	npm run build --workspace $(FRONTEND_WORKSPACE)
	npm run build --workspace $(MARKETING_WORKSPACE)

build-image: ## Build backend Docker image
	docker compose build app

# Development

dev-frontend: ## Start frontend dev server
	npm run dev --workspace $(FRONTEND_WORKSPACE)

dev-marketing: ## Start marketing dev server
	npm run dev --workspace $(MARKETING_WORKSPACE)

# Runtime and database

db-up: ## Start Postgres
	docker compose up -d db

db-down: ## Stop Postgres
	docker compose stop db

migrate: ## Run database migrations
	cd $(BACKEND_DIR) && uv run verasig migrate

db-migrate: migrate ## Alias for migrate

health: ## Check backend health through the local CLI
	cd $(BACKEND_DIR) && uv run verasig health

up: ## Start all services with rebuilds
	docker compose up --build

down: ## Stop and remove local services
	docker compose down

logs: ## Follow backend app logs
	docker compose logs -f app

cli: ## Run backend CLI command, e.g. make cli ARGS="stats <channel>"
	cd $(BACKEND_DIR) && uv run verasig $(ARGS)

# Cleanup

clean: ## Remove safe generated artifacts
	rm -rf apps/frontend/dist apps/marketing/dist
	rm -rf apps/frontend/.vite apps/marketing/.vite libs/design-system/.vite
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} +
	find $(BACKEND_DIR) -type d -name .pytest_cache -exec rm -rf {} +
	find $(BACKEND_DIR) -type d -name .ruff_cache -exec rm -rf {} +
	find $(BACKEND_DIR) -type f -name '*.pyc' -delete

clean-all: clean ## Remove dependencies and local virtual environments
	rm -rf node_modules apps/frontend/node_modules apps/marketing/node_modules
	rm -rf libs/design-system/node_modules apps/backend/.venv

# Compatibility aliases

fe-install: install-web ## Alias for install-web

fe-dev: dev-frontend ## Alias for dev-frontend

fe-build: build-web ## Alias for build-web

fe-test: test-web ## Alias for test-web

fe-lint: lint-web ## Alias for lint-web

be-install: install-backend ## Alias for install-backend

be-test: test-backend ## Alias for test-backend

be-lint: lint-backend ## Alias for lint-backend

be-format: format-backend ## Alias for format-backend
