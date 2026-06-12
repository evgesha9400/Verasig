.DEFAULT_GOAL := help

BACKEND_DIR := apps/backend
FRONTEND_DIR := apps/frontend
ARGS ?= --help

.PHONY: help doctor env \
        install install-backend install-frontend \
        check format format-check lint test build build-image \
        backend-format backend-format-check backend-lint backend-test \
        frontend-format frontend-format-check frontend-lint frontend-test frontend-build \
        dev-frontend dev-marketing \
        db-up db-down migrate db-migrate health \
        up down logs cli clean clean-all \
        fe-install fe-dev fe-build fe-test fe-lint \
        be-install be-test be-lint be-format

help: ## Show available root targets
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

doctor: ## Verify root-level developer tools
	@command -v docker >/dev/null
	@command -v make >/dev/null
	@$(MAKE) -C $(FRONTEND_DIR) doctor
	@$(MAKE) -C $(BACKEND_DIR) doctor
	@docker compose version >/dev/null
	@echo "OK: root toolchain is available"

env: ## Create root .env from .env.example when missing
	@if [ ! -f .env ]; then cp .env.example .env; fi

# Setup

install: install-frontend install-backend ## Install frontend and backend dependencies

install-frontend: ## Install frontend workspace dependencies
	$(MAKE) -C $(FRONTEND_DIR) install

install-backend: ## Install backend dependencies
	$(MAKE) -C $(BACKEND_DIR) install

# Quality gates

check: format-check lint test build ## Run the full local verification gate

format: frontend-format backend-format ## Format frontend and backend code

format-check: frontend-format-check backend-format-check ## Check frontend and backend formatting

lint: frontend-lint backend-lint ## Lint frontend and backend code

test: backend-test frontend-test ## Run backend and frontend tests

build: frontend-build build-image ## Build frontend apps and backend image

frontend-format: ## Format frontend workspace files
	$(MAKE) -C $(FRONTEND_DIR) format

frontend-format-check: ## Check frontend workspace formatting
	$(MAKE) -C $(FRONTEND_DIR) format-check

frontend-lint: ## Lint frontend workspace
	$(MAKE) -C $(FRONTEND_DIR) lint

frontend-test: ## Run frontend workspace tests
	$(MAKE) -C $(FRONTEND_DIR) test

frontend-build: ## Build frontend workspace apps
	$(MAKE) -C $(FRONTEND_DIR) build

backend-format: ## Format backend Python
	$(MAKE) -C $(BACKEND_DIR) format

backend-format-check: ## Check backend Python formatting
	$(MAKE) -C $(BACKEND_DIR) format-check

backend-lint: ## Lint backend Python
	$(MAKE) -C $(BACKEND_DIR) lint

backend-test: ## Run backend tests
	$(MAKE) -C $(BACKEND_DIR) test

build-image: ## Build backend Docker image
	docker compose build app

# Development

dev-frontend: ## Start product frontend dev server
	$(MAKE) -C $(FRONTEND_DIR) dev-product

dev-marketing: ## Start marketing dev server
	$(MAKE) -C $(FRONTEND_DIR) dev-marketing

# Runtime and database

db-up: ## Start Postgres
	docker compose up -d db

db-down: ## Stop Postgres
	docker compose stop db

migrate: ## Run database migrations
	$(MAKE) -C $(BACKEND_DIR) migrate

db-migrate: migrate ## Alias for migrate

health: ## Check backend health through the local CLI
	$(MAKE) -C $(BACKEND_DIR) health

up: ## Start all services with rebuilds
	docker compose up --build

down: ## Stop and remove local services
	docker compose down

logs: ## Follow backend app logs
	docker compose logs -f app

cli: ## Run backend CLI command, e.g. make cli ARGS="stats <channel>"
	$(MAKE) -C $(BACKEND_DIR) cli ARGS="$(ARGS)"

# Cleanup

clean: ## Remove safe generated artifacts
	$(MAKE) -C $(FRONTEND_DIR) clean
	$(MAKE) -C $(BACKEND_DIR) clean

clean-all: ## Remove dependencies and local virtual environments
	$(MAKE) -C $(FRONTEND_DIR) clean-all
	$(MAKE) -C $(BACKEND_DIR) clean-all

# Compatibility aliases

fe-install: install-frontend ## Alias for install-frontend

fe-dev: dev-frontend ## Alias for dev-frontend

fe-build: frontend-build ## Alias for frontend-build

fe-test: frontend-test ## Alias for frontend-test

fe-lint: frontend-lint ## Alias for frontend-lint

be-install: install-backend ## Alias for install-backend

be-test: backend-test ## Alias for backend-test

be-lint: backend-lint ## Alias for backend-lint

be-format: backend-format ## Alias for backend-format
