.DEFAULT_GOAL := help

ARGS ?= --help

.PHONY: help doctor install format format-check lint test test-unit test-integration \
        migrate health cli clean clean-all

help: ## Show backend targets
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

doctor: ## Verify backend developer tools
	@command -v uv >/dev/null
	@echo "OK: backend toolchain is available"

install: ## Install backend dependencies
	uv sync --all-groups

format: ## Format backend Python
	uv run ruff format . && uv run ruff check --fix .

format-check: ## Check backend Python formatting
	uv run ruff format --check . && uv run ruff check .

lint: ## Lint backend Python
	uv run ruff check .

test: ## Run backend tests
	uv run pytest

test-unit: ## Run backend unit tests
	uv run pytest tests/unit

test-integration: ## Run backend integration tests
	uv run pytest tests/integration

migrate: ## Run database migrations
	uv run verasig migrate

health: ## Check backend health through the local CLI
	uv run verasig health

cli: ## Run backend CLI command, e.g. make cli ARGS="stats <channel>"
	uv run verasig $(ARGS)

clean: ## Remove safe backend generated artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

clean-all: clean ## Remove backend virtual environment
	rm -rf .venv
