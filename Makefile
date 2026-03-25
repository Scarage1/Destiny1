.PHONY: help dev stop test lint coverage ingest gate clean docker-build docker-run

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

dev: ## Start backend + frontend (background)
	bash scripts/dev_up.sh

stop: ## Stop all services
	bash scripts/dev_down.sh

test: ## Run backend pytest + frontend vitest
	bash -c "source .venv/bin/activate && python -m pytest -q"
	cd frontend && npm test

lint: ## Run ruff linter against backend
	bash -c "source .venv/bin/activate && ruff check backend/"

coverage: ## Run backend tests with coverage report
	bash -c "source .venv/bin/activate && python -m pytest --cov=backend --cov-report=term-missing"

ingest: ## Run data ingestion pipeline
	bash -c "source .venv/bin/activate && python -m backend.ingest"

gate: ## Run full quality gate (lint + tests + build + API smoke)
	bash scripts/quality_gate.sh

docker-build: ## Build production Docker image
	docker build -t o2c-intelligence:latest .

docker-run: ## Run production Docker image locally
	docker run --rm -p 8000:8000 --env-file .env o2c-intelligence:latest

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ | grep -v .venv | xargs rm -rf
	find . -type d -name .pytest_cache | grep -v .venv | xargs rm -rf
	find . -type d -name .ruff_cache | grep -v .venv | xargs rm -rf
	rm -f .coverage
	rm -rf frontend/dist
