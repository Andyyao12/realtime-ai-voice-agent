.PHONY: install lint test typecheck web-check build security readme-check compose-check

install:
	uv sync --dev
	cd web && corepack pnpm install --frozen-lockfile

lint:
	uv run ruff check .
	uv run ruff format --check .
	cd web && corepack pnpm lint

test:
	uv run pytest
	cd web && corepack pnpm test

typecheck:
	uv run mypy src tests

web-check:
	cd web && corepack pnpm typecheck
	cd web && corepack pnpm build

build:
	docker build -f Dockerfile.python -t harborlight-agent:local .
	docker build -f web/Dockerfile -t harborlight-web:local web

security:
	uv run python scripts/security_scan.py
	uv run pip-audit
	cd web && corepack pnpm --registry=https://registry.npmjs.org audit

readme-check:
	uv run python scripts/readme_check.py

compose-check:
	docker compose --env-file .env.example config --quiet
