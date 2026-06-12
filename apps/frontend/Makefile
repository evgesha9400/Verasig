.DEFAULT_GOAL := help

WEB_WORKSPACE := verasig-web
DESIGN_SYSTEM_WORKSPACE := @verasig/design-system

.PHONY: help doctor install format format-check lint test test-web \
        test-design-system build build-web dev clean clean-all

help: ## Show frontend targets
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

doctor: ## Verify frontend developer tools
	@command -v npm >/dev/null
	@echo "OK: frontend toolchain is available"

install: ## Install frontend workspace dependencies
	npm ci

format: ## Format frontend workspace files
	npm run format

format-check: ## Check frontend workspace formatting
	npm run format:check

lint: ## Lint frontend workspace packages
	npm run lint

test: test-design-system test-web ## Run frontend workspace tests

test-design-system: ## Run design-system tests
	npm run test --workspace $(DESIGN_SYSTEM_WORKSPACE)

test-web: ## Run unified frontend app tests once
	npm run test --workspace $(WEB_WORKSPACE) -- --run

build: build-web ## Build unified frontend app

build-web: ## Build unified frontend app
	npm run build --workspace $(WEB_WORKSPACE)

dev: ## Start unified frontend dev server
	npm run dev --workspace $(WEB_WORKSPACE)

clean: ## Remove safe frontend generated artifacts
	rm -rf web/dist web/.vite design-system/.vite

clean-all: clean ## Remove frontend dependencies
	rm -rf node_modules web/node_modules design-system/node_modules
