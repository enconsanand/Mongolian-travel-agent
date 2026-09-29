folder=$(shell basename $(CURDIR))

.PHONY: help
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

clear-caches:
	rm -rf .ruff_cache
	rm -rf ./back/.ruff_cache
	rm -rf ./back/.mypy_cache
	rm -rf ./back/.pytest_cache

clear-nuxt:
	rm -rf .nuxt
	rm -rf ./front/.nuxt
	rm -rf ./front/.pnpm-store
	rm -rf ./front/.output

clear-front: clear-nuxt
	docker volume rm -f ${folder}_node_modules

clear-uv-cache: clear-caches
	docker volume rm -f ${folder}_uv_cache

clear-db:
	docker volume rm -f ${folder}_db_data

clear: clear-front clear-uv-cache clear-db ## Clear all temporary files and volumes


######################## LOCAL ENVIRONMENT #############################

local-setup: ## Setup local development environment
	rm -rf .venv && cp back/uv.lock . && cp back/pyproject.toml . && cp back/.python-version . && \
		uv sync && rm uv.lock pyproject.toml .python-version
	rm -rf node_modules && cp front/.nvmrc . && cp front/package.json . && cp front/pnpm-lock.yaml . && cp front/pnpm-workspace.yaml . && \
        source $(HOME)/.nvm/nvm.sh && nvm use && pnpm install && rm .nvmrc package.json pnpm-lock.yaml pnpm-workspace.yaml

uv-update: down clear-uv-cache
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm back uv lock --upgrade

pnpm-update: down clear-front
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm front pnpm install --force
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm front pnpm update --latest

build: ## Build docker images
	docker compose -f docker-compose.yml --env-file ./secret/.env build

up: ## Start the application
	docker compose -f docker-compose.yml --env-file ./secret/.env up

up-back: ## Start only backend in detached mode
	docker compose -f docker-compose.yml --env-file ./secret/.env up -d

down: ## Stop and remove containers
	docker compose -f docker-compose.yml --env-file ./secret/.env down

bash-back:
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm back bash

bash-front:
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm front sh

seed: ## Load data/mock into MongoDB, create login users and indexes (keeps trips, bookings, payments)
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm back bash -c "export PYTHONPATH=. && uv run python ./app/seeder.py"

seed-reset: ## Like seed, but also replaces trips, bookings, payments and availability with the demo data
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm back bash -c "export PYTHONPATH=. && uv run python ./app/seeder.py --reset"

ruff-sort:
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm back uv run ruff check --select I --fix

ruff-check:
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm back uv run ruff check

ruff-format:
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm back uv run ruff format

mypy:
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm back uv run mypy

prettier:
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm front pnpm format:write

eslint:
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm front pnpm lint

ts-check:
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm front pnpm typescript:check

lint: ruff-sort ruff-check ruff-format mypy prettier eslint ts-check ## Run all linters and formatters

test: ## Run backend tests
	docker compose -f docker-compose.yml --env-file ./secret/.env run --rm back uv run pytest

install: down clear build seed down up ## Full clean installation and startup


######################## PRODUCTION ENVIRONMENT #############################
