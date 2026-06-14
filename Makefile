.DEFAULT_GOAL := help

BACKEND_DIR := apps/backend
BACKEND_ENV_FILE := $(BACKEND_DIR)/.env
COMPOSE := docker compose --env-file $(BACKEND_ENV_FILE)
FRONTEND_DIR := apps/frontend

.PHONY: help doctor env \
        install install-backend install-frontend \
        check format format-check lint test build build-image \
        backend-format backend-format-check backend-lint backend-test \
        frontend-format frontend-format-check frontend-lint frontend-test frontend-build \
        dev dev-frontend \
        db-up db-down migrate health serve \
        up down logs clean clean-all

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

env: ## Create backend .env from backend .env.example when missing
	@if [ ! -f $(BACKEND_ENV_FILE) ]; then cp $(BACKEND_DIR)/.env.example $(BACKEND_ENV_FILE); fi

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

build: frontend-build build-image ## Build frontend app and backend image

frontend-format: ## Format frontend workspace files
	$(MAKE) -C $(FRONTEND_DIR) format

frontend-format-check: ## Check frontend workspace formatting
	$(MAKE) -C $(FRONTEND_DIR) format-check

frontend-lint: ## Lint frontend workspace
	$(MAKE) -C $(FRONTEND_DIR) lint

frontend-test: ## Run frontend workspace tests
	$(MAKE) -C $(FRONTEND_DIR) test

frontend-build: ## Build frontend workspace app
	$(MAKE) -C $(FRONTEND_DIR) build

backend-format: ## Format backend Python
	$(MAKE) -C $(BACKEND_DIR) format

backend-format-check: ## Check backend Python formatting
	$(MAKE) -C $(BACKEND_DIR) format-check

backend-lint: ## Lint backend Python
	$(MAKE) -C $(BACKEND_DIR) lint

backend-test: ## Run backend tests
	$(MAKE) -C $(BACKEND_DIR) test

build-image: env ## Build backend Docker image
	$(COMPOSE) build app

# Development

dev: env db-up migrate ## DB in Docker; backend + frontend locally with hot reload
	@echo "API -> http://localhost:8000   Web -> http://localhost:5173   (Ctrl-C stops both)"
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) -C $(BACKEND_DIR) serve & \
	$(MAKE) -C $(FRONTEND_DIR) dev & \
	wait

dev-frontend: ## Start unified frontend dev server
	$(MAKE) -C $(FRONTEND_DIR) dev

# Runtime and database

db-up: env ## Start Postgres
	$(COMPOSE) up -d --wait db

db-down: env ## Stop Postgres
	$(COMPOSE) stop db

migrate: ## Run database migrations
	$(MAKE) -C $(BACKEND_DIR) migrate

health: ## Check local API health
	$(MAKE) -C $(BACKEND_DIR) health

serve: ## Run the backend API server locally
	$(MAKE) -C $(BACKEND_DIR) serve

up: env ## Start DB, migrations, backend API, and frontend
	$(COMPOSE) up --build frontend

down: env ## Stop and remove local services
	$(COMPOSE) down

logs: env ## Follow local service logs
	$(COMPOSE) logs -f

# Cleanup

clean: ## Remove safe generated artifacts
	$(MAKE) -C $(FRONTEND_DIR) clean
	$(MAKE) -C $(BACKEND_DIR) clean

clean-all: ## Remove dependencies and local virtual environments
	$(MAKE) -C $(FRONTEND_DIR) clean-all
	$(MAKE) -C $(BACKEND_DIR) clean-all
