.PHONY: help dev stop test coverage ingest gate clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

dev: ## Start backend + frontend (background)
	bash scripts/dev_up.sh

stop: ## Stop all services
	bash scripts/dev_down.sh

test: ## Run backend pytest + frontend vitest
	bash -c "source .venv/bin/activate && python -m pytest -q"
	cd frontend && npm test

coverage: ## Run backend tests with coverage report
	bash -c "source .venv/bin/activate && python -m pytest --cov=backend --cov-report=term-missing"

ingest: ## Run data ingestion pipeline
	bash -c "source .venv/bin/activate && python -m backend.ingest"

gate: ## Run full quality gate (tests + build + API smoke)
	bash scripts/quality_gate.sh

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ | grep -v .venv | xargs rm -rf
	find . -type d -name .pytest_cache | grep -v .venv | xargs rm -rf
	rm -f .coverage
	rm -rf frontend/dist
