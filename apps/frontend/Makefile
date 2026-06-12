.DEFAULT_GOAL := help

PRODUCT_WORKSPACE := verasig-frontend
MARKETING_WORKSPACE := verasig-marketing
DESIGN_SYSTEM_WORKSPACE := @verasig/design-system

.PHONY: help doctor install format format-check lint test test-product test-marketing \
        test-design-system build build-product build-marketing \
        dev-product dev-marketing clean clean-all

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

test: test-design-system test-product test-marketing ## Run frontend workspace tests

test-design-system: ## Run design-system tests
	npm run test --workspace $(DESIGN_SYSTEM_WORKSPACE)

test-product: ## Run product frontend tests once
	npm run test --workspace $(PRODUCT_WORKSPACE) -- --run

test-marketing: ## Run marketing tests once
	npm run test --workspace $(MARKETING_WORKSPACE) -- --run

build: build-product build-marketing ## Build product and marketing apps

build-product: ## Build product frontend app
	npm run build --workspace $(PRODUCT_WORKSPACE)

build-marketing: ## Build marketing app
	npm run build --workspace $(MARKETING_WORKSPACE)

dev-product: ## Start product frontend dev server
	npm run dev --workspace $(PRODUCT_WORKSPACE)

dev-marketing: ## Start marketing dev server
	npm run dev --workspace $(MARKETING_WORKSPACE)

clean: ## Remove safe frontend generated artifacts
	rm -rf product/dist product/.vite marketing/dist marketing/.vite design-system/.vite

clean-all: clean ## Remove frontend dependencies
	rm -rf node_modules product/node_modules marketing/node_modules design-system/node_modules
